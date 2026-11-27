import express from "express";
import { randomUUID } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
const router=express.Router();
const file=resolve(process.env.NEXUS_APPLICATIONS_FILE||"./data/applications.json");
const applications=new Map();
const statuses=new Set(["saved","researching","draft_ready","approved_to_apply","applied","interview","offer","rejected","withdrawn"]);
function load(){try{const data=JSON.parse(readFileSync(file,"utf8"));if(Array.isArray(data))for(const a of data)if(a?.id)applications.set(a.id,a)}catch(e){if(e.code!=="ENOENT")console.error("Applications store error",e.message)}}
function save(){mkdirSync(dirname(file),{recursive:true});writeFileSync(file,JSON.stringify([...applications.values()],null,2),{encoding:"utf8",mode:0o600})}
load();
router.use((req,res,next)=>{const token=process.env.APP_ACCESS_TOKEN,supplied=(req.headers.authorization||"").replace(/^Bearer\\s+/i,"");if(!token)return res.status(503).json({error:"APP_ACCESS_TOKEN missing"});if(!supplied||supplied!==token)return res.status(401).json({error:"Unauthorized"});next()});
router.get("/",(_req,res)=>res.json({applications:[...applications.values()],storage:"local JSON file"}));
router.post("/",(req,res)=>{const b=req.body||{};if(typeof b.company!=="string"||!b.company.trim()||typeof b.role!=="string"||!b.role.trim())return res.status(400).json({error:"Company and role required"});const item={id:randomUUID(),company:b.company.trim(),role:b.role.trim(),url:typeof b.url==="string"?b.url.trim():"",notes:typeof b.notes==="string"?b.notes.trim():"",status:"saved",createdAt:new Date().toISOString(),updatedAt:new Date().toISOString()};applications.set(item.id,item);try{save()}catch(e){applications.delete(item.id);return res.status(500).json({error:"Save failed"})}res.status(201).json({application:item})});
router.patch("/:id",(req,res)=>{const item=applications.get(req.params.id);if(!item)return res.status(404).json({error:"Application not found"});const {status,notes,url}=req.body||{};if(status!==undefined&&!statuses.has(status))return res.status(400).json({error:"Invalid status"});const prev={...item};if(status)item.status=status;if(typeof notes==="string")item.notes=notes.trim();if(typeof url==="string")item.url=url.trim();item.updatedAt=new Date().toISOString();try{save()}catch(e){Object.assign(item,prev);return res.status(500).json({error:"Save failed"})}res.json({application:item})});
router.delete("/:id",(req,res)=>{const item=applications.get(req.params.id);if(!item)return res.status(404).json({error:"Not found"});applications.delete(item.id);try{save()}catch(e){applications.set(item.id,item);return res.status(500).json({error:"Save failed"})}res.json({deleted:true})});
export default router;

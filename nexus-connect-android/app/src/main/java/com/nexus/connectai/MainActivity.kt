package com.nexus.connectai

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 48, 32, 32)
            gravity = Gravity.CENTER_HORIZONTAL
        }

        val title = TextView(this).apply {
            text = "NEXUS Connect AI"
            textSize = 26f
        }
        val subtitle = TextView(this).apply {
            text = "Client calling workspace • AI-assisted workflow"
            textSize = 14f
            setPadding(0, 12, 0, 28)
        }
        val number = EditText(this).apply {
            hint = "Client phone number (include country code)"
            inputType = 3
            singleLine = true
        }
        val dial = Button(this).apply {
            text = "Review number in phone dialer"
            setOnClickListener {
                val value = number.text.toString().trim()
                if (value.length < 7) {
                    Toast.makeText(this@MainActivity, "Enter a valid phone number.", Toast.LENGTH_SHORT).show()
                } else {
                    val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + Uri.encode(value)))
                    startActivity(intent)
                }
            }
        }
        val note = TextView(this).apply {
            text = "Your phone opens its dialer. You review the number and tap Call yourself. No call is made automatically."
            textSize = 13f
            setPadding(0, 20, 0, 20)
        }
        val status = TextView(this).apply {
            text = "AI voice calling: not connected yet\nBackend, telephony provider, and secure Realtime media bridge are required."
            textSize = 14f
        }

        root.addView(title)
        root.addView(subtitle)
        root.addView(number, LinearLayout.LayoutParams(-1, -2))
        root.addView(dial)
        root.addView(note)
        root.addView(status)
        setContentView(root)
    }
}

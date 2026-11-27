package com.nexus.connectai

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private fun label(value: String, size: Float = 14f) = TextView(this).apply {
        text = value
        textSize = size
        setPadding(0, 12, 0, 12)
    }

    private fun actionButton(value: String, onClick: () -> Unit) = Button(this).apply {
        text = value
        setOnClickListener { onClick() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 36, 32, 32)
            gravity = Gravity.CENTER_HORIZONTAL
        }

        root.addView(label("NEXUS Connect AI", 28f))
        root.addView(label("Client communication workspace • Android", 14f))

        val number = EditText(this).apply {
            hint = "Client phone number with country code"
            inputType = 3
            singleLine = true
        }
        root.addView(number, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        root.addView(actionButton("Review phone number in dialer") {
            val value = number.text.toString().trim()
            if (value.length < 7) {
                Toast.makeText(this, "Enter a valid phone number.", Toast.LENGTH_SHORT).show()
            } else {
                runCatching {
                    startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + Uri.encode(value))))
                }.onFailure {
                    Toast.makeText(this, "No compatible dialer app found.", Toast.LENGTH_LONG).show()
                }
            }
        })

        root.addView(label("Video meeting", 18f))
        root.addView(label("Open Google Meet to create or join a meeting. You choose the participants and start the meeting yourself."))
        root.addView(actionButton("Open Google Meet") {
            val meet = Intent(Intent.ACTION_VIEW, Uri.parse("https://meet.google.com/new"))
            runCatching { startActivity(meet) }.onFailure {
                Toast.makeText(this, "Unable to open a browser or meeting app.", Toast.LENGTH_LONG).show()
            }
        })

        root.addView(label("AI calling integration: not connected", 18f))
        root.addView(label(
            "This version opens your phone dialer and Google Meet. It does not place calls automatically, connect live AI audio, record conversations, or contact clients. A secure telephony provider and deployed realtime media backend are still required."
        ))
        root.addView(label(
            "Safety: verify the number and recipient, obtain any required consent, and tap Call or start the meeting yourself."
        ))

        setContentView(root)
    }
}

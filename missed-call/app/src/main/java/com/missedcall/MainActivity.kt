package com.missedcall

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.missedcall.data.calllog.PhoneKey
import com.missedcall.data.db.AppDatabase
import com.missedcall.data.db.TrackedContact
import com.missedcall.work.WorkScheduler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * PHASE 1 minimal harness (ARCHITECTURE.md Phase 1). Not the real UI — that's Phase 3 (Frontend).
 * This screen only exists to exercise the risky primitive end-to-end:
 *   - request the runtime permissions (READ_CALL_LOG / READ_CONTACTS / POST_NOTIFICATIONS),
 *   - seed ONE tracked contact from a manually-entered number + cadence,
 *   - trigger the check on demand so we can verify a real notification fires without waiting a day.
 */
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { padding ->
                    Phase1Harness(Modifier.padding(padding))
                }
            }
        }
    }
}

@Composable
private fun Phase1Harness(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var number by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("Test Contact") }
    var cadence by remember { mutableStateOf("21") } // §8.2 proposal default: 21 days.
    var status by remember { mutableStateOf("Ready.") }

    // Runtime permission request. Phase 1 requests all three at once; the polished 3-step first-run
    // flow with rationale screens is Phase 4 (Frontend).
    val permissions = buildList {
        add(Manifest.permission.READ_CALL_LOG)
        add(Manifest.permission.READ_CONTACTS)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
        }
    }.toTypedArray()

    val permLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        status = if (granted.values.all { it }) "All permissions granted." else
            "Some permissions denied: ${granted.filterValues { !it }.keys.joinToString()}"
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Missed Call — Phase 1 harness", style = MaterialTheme.typography.titleLarge)
        Text(
            "Grant permissions, seed one contact, then run the check to fire a real notification " +
                "if that contact is overdue.",
            style = MaterialTheme.typography.bodyMedium,
        )

        Button(onClick = { permLauncher.launch(permissions) }) { Text("1. Request permissions") }

        OutlinedTextField(
            value = name, onValueChange = { name = it },
            label = { Text("Display name") }, modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = number, onValueChange = { number = it },
            label = { Text("Phone number (any format)") }, modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = cadence, onValueChange = { cadence = it.filter(Char::isDigit) },
            label = { Text("Cadence (days)") }, modifier = Modifier.fillMaxWidth(),
        )

        Button(onClick = {
            val key = PhoneKey.of(number)
            if (key == null) {
                status = "Enter a valid phone number first."
                return@Button
            }
            val days = cadence.toIntOrNull() ?: 21
            scope.launch {
                withContext(Dispatchers.IO) {
                    val dao = AppDatabase.get(context).trackedContactDao()
                    // Phase 1: one contact only — clear any prior seed so re-seeding is idempotent.
                    dao.getAll().forEach { dao.delete(it) }
                    dao.upsert(
                        TrackedContact(
                            lookupKey = "manual:$key",   // no ContactsContract lookup in Phase 1.
                            displayName = name.ifBlank { "Test Contact" },
                            numberKeys = key,
                            cadenceDays = days,
                        )
                    )
                }
                status = "Seeded '$name' (key=$key, cadence=${days}d)."
            }
        }) { Text("2. Seed / replace tracked contact") }

        Button(onClick = {
            WorkScheduler.runNow(context)
            status = "Enqueued check. Watch for a notification if overdue (see Logcat: DailyCheckWorker)."
        }) { Text("3. Run check now") }

        Text(status, style = MaterialTheme.typography.bodyMedium)
    }
}

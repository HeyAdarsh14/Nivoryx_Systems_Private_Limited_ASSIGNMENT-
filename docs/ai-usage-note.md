# AI Usage Disclosure Note

**Tool Used:** Antigravity / Gemini 3.8

**Prompt 1 (Dashboard Generation):**
> "Build a responsive tank level dashboard using vanilla HTML, CSS, JavaScript, and Chart.js based on the supplied 8 mock telemetry readings. Calculate the latest level, daily minimum, daily maximum, and show an alert if level falls below 20%."

**Prompt 2 (API Test Automation):**
> "Create a Python pytest suite that mocks the POST /login and GET /device/{id}/status endpoints. Include positive, negative, and edge test cases covering token authorization, stale timestamps, malformed schemas, and boundary percentages."

**One Thing It Got Wrong & How I Fixed It:**
> The assistant initially used a non-strict inequality (`<= 20%`) and triggered an active critical low-level alert on the main screen because one historical record reached 18% at 16:00, despite the current (latest by timestamp) reading at 20:00 being 55%. I fixed the logic to strict inequality (`level < 20%` where 20.0% is treated as safe boundary), restricted the active alert banner exclusively to the latest valid timestamp, and cleanly separated the historical 18% event into an informative historical notification and highlighted chart point.

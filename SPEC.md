# Sid: A Token-Efficient CLI for iOS Automation

## 1. Philosophy & Goals
**Sid** (Simulator Driver) is a command-line interface designed to bridge the gap between Large Language Models (LLMs) and the iOS Simulator.

* **Token Efficiency (The "Narrow Context" Principle):** Sid’s primary output is a simplified, text-based JSON representation of the UI. This allows LLMs to "see" the screen using minimal tokens, avoiding the high cost and latency of processing raw screenshots.
* **Stateless Atomic Actions:** Each command is independent. Sid does not maintain a complex session, making it easier for an Agent to reason about the state at any given step.
* **Native Wrapper:** Under the hood, Sid orchestrates `xcrun simctl` (for system tasks) and `idb` (for deep accessibility inspection).

---

## 2. Architecture
* **Interface:** `sid [command] [subcommand] [flags]`
* **Output Format:** Standard JSON (for machine parsing) or human-readable text.
* **Error Handling:** Returns strictly formatted error codes and descriptive messages to help the LLM self-correct (e.g., `ERR_ELEMENT_NOT_FOUND`, `ERR_APP_CRASHED`).

---

## 3. Core Capabilities

### 3.1. Vision (The "See" Commands)
*These commands generate the context for the LLM to understand the current state.*

#### `sid inspect`
Returns a simplified JSON tree of the current screen's accessibility hierarchy.
* **Flag:** `--interactive-only` (Default: `true`). Filters out structural containers (`Window`, `Other`) and keeps actionable elements (`Button`, `TextField`, `Cell`, `Switch`, `StaticText`).
* **Flag:** `--depth [n]`. Limits the hierarchy depth to save tokens.
* **Flag:** `--flat`. Return a flat list of elements instead of a hierarchy (Backward Compatibility).
* **Output Schema (Hierarchical):**
    ```json
    {
      "app": "com.example.myapp",
      "screen_id": "LoginView",
      "elements": [
        {
          "type": "NavigationBar",
          "children": [
            { "type": "Button", "label": "Back" }
          ]
        },
        {
          "type": "TextField",
          "id": "email_field",
          "label": "Email Address",
          "value": "",
          "frame": "20,100,300,40"
        },
        {
          "type": "Button",
          "id": "login_btn",
          "label": "Log In",
          "enabled": false
        }
      ]
    }
    ```

#### `sid screenshot`
Captures the visual state for verification or multimodal fallback.
* **Args:** `[filename]`
* **Flag:** `--mask-text` (Optional). Redacts text for privacy/security before saving.

---

### 3.2. Interaction (The "Act" Commands)
*Direct manipulation of the app UI.*

#### `sid tap`
Taps a UI element.
* **Targeting Logic:** Accepts a string query.
    1.  **Exact Match:** Accessibility Identifier.
    2.  **Fuzzy Match:** Label text (e.g., "Login" matches "Log In").
    3.  **Coordinate Fallback:** `--x [num] --y [num]`.
* **Example:** `sid tap "Sign Up"`

#### `sid type`
Inputs text into the currently focused field.
* **Args:** `[text_string]`
* **Flag:** `--submit` (Default: `false`). Hits "Return/Enter" on the keyboard after typing.
* **Example:** `sid type "user@example.com" --submit`

#### `sid scroll`
* **Args:** `[direction]` (`up`, `down`, `left`, `right`).
* **Flag:** `--until-visible [element_label]`. A specialized loop that scrolls until a specific element appears in the `inspect` tree.

#### `sid gesture`
* **Swipe:** `sid gesture swipe [start_x],[start_y] [end_x],[end_y]`
* **Pinch:** `sid gesture pinch [in|out]`

---

### 3.3. System & Environment (The "God Mode")
*Developers need to test how the app behaves under different system conditions.*

#### `sid launch`
* **Args:** `[bundle_id]`
* **Flag:** `--clean`. Wipes the app container (simulates a fresh install).
* **Flag:** `--args "[key]=[value]"`. Passes Launch Arguments (e.g., `-TakingScreenshots YES`).
* **Flag:** `--locale [code]`. Launches the app in a specific language (e.g., `es-MX`).

#### `sid open`
Opens a URL scheme or Universal Link to test routing.
* **Args:** `[url]`
* **Example:** `sid open "myapp://settings/profile?edit=true"`

#### `sid permission`
Manages TCC (Privacy) permissions to test "Happy Path" vs. "Denied Path".
* **Args:** `[service] [status]`
* **Services:** `camera`, `photos`, `location`, `microphone`, `contacts`, `calendar`.
* **Status:** `grant`, `deny`, `reset`.
* **Example:** `sid permission camera deny`

#### `sid location`
Simulates GPS coordinates.
* **Args:** `[lat] [lon]`
* **Example:** `sid location 37.7749 -122.4194` (San Francisco)

#### `sid network` (Advanced)
* **Args:** `[condition]`
* **Options:** `wifi`, `cellular`, `offline`.

---

### 3.4. Verification & Debugging (The "Check" Commands)
*Tools for the LLM to verify success or diagnose failure.*

#### `sid assert`
Quick boolean check for LLM usage.
* **Args:** `[element_query] [state]`
* **States:** `exists`, `visible`, `hidden`, `text=[value]`.
* **Output:** `PASS` or `FAIL: Element found but text was 'Cancel', expected 'Submit'`.

#### `sid logs`
Fetches the tail of the system log for the target app.
* **Flag:** `--crash-report`. Checks if a crash log was generated in the last session and outputs the stack trace.
* **Use Case:** "The app closed unexpectedly. Why?"

#### `sid tree`
Lists files in the app's sandbox.
* **Args:** `[directory]` (`documents`, `caches`, `tmp`).
* **Use Case:** Verifying that a file download or database export actually occurred.

---

## 4. Sample Agent Workflow

**Objective:** "Verify that the app handles denied Camera permissions gracefully."

1.  `sid launch com.myapp.beta --clean`
2.  `sid inspect` -> Finds "Start Scan" button.
3.  `sid permission camera deny` (Pre-emptively deny permission).
4.  `sid tap "Start Scan"`
5.  `sid inspect`
    * **Agent Logic:** Looks for an alert with text "Camera Permission Needed" or "Open Settings".
    * **If found:** `sid assert "Open Settings" visible` -> Returns `PASS`.
    * **If not found:** Agent marks test as `FAILED` (App likely stalled or crashed).

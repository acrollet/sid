# Sid: A Token-Efficient CLI for iOS Automation

**Sid** (Simulator Driver) is a command-line interface designed to bridge the gap between Large Language Models (LLMs) and the iOS Simulator. It provides a set of stateless, atomic commands to inspect, interact with, and verify the state of iOS applications running in the Simulator.

## Features

*   **Token Efficiency:** Generates simplified, text-based JSON representations of the UI, allowing LLMs to "see" the screen with minimal token usage.
*   **Stateless Actions:** Each command is independent, making it easier for agents to reason about the state.
*   **Native Wrapper:** Orchestrates `xcrun simctl` and `idb` for robust automation.

## Installation

You can run Sid directly using `uvx` (recommended):

```bash
uvx sid --help
```

Or install it via pip:

```bash
pip install sid
```

*Note: You must have `idb` (iOS Development Bridge) and Xcode command-line tools installed and configured on your machine.*

## Usage

Sid commands follow the structure: `sid [command] [subcommand] [flags]`

### Vision (Seeing the Screen)

*   **Inspect UI:** Get a JSON representation of the current screen.
    ```bash
    sid inspect --interactive-only
    ```
*   **Take Screenshot:** Capture the visual state.
    ```bash
    sid screenshot output.png
    ```

### Interaction (Acting on the App)

*   **Tap Element:** Tap by accessibility identifier or label text.
    ```bash
    sid tap "Log In"
    ```
*   **Type Text:** Enter text into the focused field.
    ```bash
    sid type "user@example.com" --submit
    ```
*   **Scroll:** Scroll in a direction, optionally until an element is found.
    ```bash
    sid scroll down --until-visible "Submit"
    ```
*   **Gestures:** Perform swipes.
    ```bash
    sid gesture swipe 100,200 100,400
    ```

### System (Controlling the Environment)

*   **Launch App:** Launch an app by Bundle ID.
    ```bash
    sid launch com.example.myapp --clean
    ```
*   **Open URL:** Open a deep link.
    ```bash
    sid open "myapp://settings"
    ```
*   **Permissions:** Manage privacy permissions.
    ```bash
    sid permission camera grant
    ```
*   **Location:** Set simulated GPS coordinates.
    ```bash
    sid location 37.7749 -122.4194
    ```

### Verification (Checking State)

*   **Assert:** Verify UI state (exists, visible, hidden, text matches).
    ```bash
    sid assert "Welcome Message" visible
    ```
*   **Logs:** Fetch recent app logs.
    ```bash
    sid logs --crash-report
    ```
*   **File Tree:** List files in the app's sandbox.
    ```bash
    sid tree documents
    ```

## Contributing

1.  Clone the repository.
2.  Install dependencies.
3.  Run tests: `python3 -m unittest discover tests`

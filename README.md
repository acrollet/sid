# Pippin: A Token-Efficient CLI for iOS Automation

**Pippin** (Simulator Driver) is a command-line interface designed to bridge the gap between Large Language Models (LLMs) and the iOS Simulator. It provides a set of stateless, atomic commands to inspect, interact with, and verify the state of iOS applications running in the Simulator.

## Features

*   **Token Efficiency:** Generates simplified, text-based JSON representations of the UI, allowing LLMs to "see" the screen with minimal token usage.
*   **Stateless Actions:** Each command is independent, making it easier for agents to reason about the state.
*   **Native Wrapper:** Orchestrates `xcrun simctl` and `idb` for robust automation.

## Installation

You can run Pippin directly using `uvx` (recommended):

```bash
uvx pippin --help
```

Or install it via pip:

```bash
pip install pippin
```

*Note: You must have `idb` (iOS Development Bridge) and Xcode command-line tools installed and configured on your machine.*

## Usage

Pippin commands follow the structure: `pippin [command] [subcommand] [flags]`

### Vision (Seeing the Screen)

*   **Inspect UI:** Get a JSON representation of the current screen.
    ```bash
    pippin inspect --interactive-only
    ```
*   **Take Screenshot:** Capture the visual state.
    ```bash
    pippin screenshot output.png
    ```

### Interaction (Acting on the App)

*   **Tap Element:** Tap by accessibility identifier or label text.
    ```bash
    pippin tap "Log In"
    ```
*   **Type Text:** Enter text into the focused field.
    ```bash
    pippin type "user@example.com" --submit
    ```
*   **Scroll:** Scroll in a direction, optionally until an element is found.
    ```bash
    pippin scroll down --until-visible "Submit"
    ```
*   **Gestures:** Perform swipes.
    ```bash
    pippin gesture swipe 100,200 100,400
    ```

### System (Controlling the Environment)

*   **Launch App:** Launch an app by Bundle ID.
    ```bash
    pippin launch com.example.myapp --clean
    ```
*   **Open URL:** Open a deep link.
    ```bash
    pippin open "myapp://settings"
    ```
*   **Permissions:** Manage privacy permissions.
    ```bash
    pippin permission camera grant
    ```
*   **Location:** Set simulated GPS coordinates.
    ```bash
    pippin location 37.7749 -122.4194
    ```

### Verification (Checking State)

*   **Assert:** Verify UI state (exists, visible, hidden, text matches).
    ```bash
    pippin assert "Welcome Message" visible
    ```
*   **Logs:** Fetch recent app logs.
    ```bash
    pippin logs --crash-report
    ```
*   **File Tree:** List files in the app's sandbox.
    ```bash
    pippin tree documents
    ```

## Contributing

1.  Clone the repository.
2.  Install dependencies.
3.  Run tests: `python3 -m unittest discover tests`

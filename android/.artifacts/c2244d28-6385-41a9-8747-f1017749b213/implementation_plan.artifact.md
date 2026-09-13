# Refine Mobile UI to Match PC Version

This plan outlines the changes to `MainActivity.kt` to synchronize the mobile app's UI/UX with the desktop version, including design refinements, persistent login, and expanded settings.

## User Review Required

> [!IMPORTANT]
> The UI layout will be updated to match the PC version's metric blocks and status strips.
> Permissions for audio and notifications will be requested if not already granted.

## Proposed Changes

### [Component] Android Mobile App

#### [MODIFY] [MainActivity.kt](file:///C:/Users/1tekn/OneDrive/Belgeler/LyrenaAI/android/app/src/main/java/com/lyrenaai/MainActivity.kt)

- **Constants & Colors**: Update theme colors (BG, PANEL, TEXT, IDLE, READY, BUSY, etc.) to match `core/config.py`.
- **UI Layout (HUD)**:
    - Update Header: Include a Hamburger menu icon (☰) in the top-left.
    - Update Metrics: Redesign the bottom metrics row to match the `MetricBlock` style (Title in muted small text, Value in bold).
    - Update Status: Add a status strip at the bottom of the main content area.
- **OrbView Refinement**:
    - Standby/Ready state: Draw a single clean ring.
    - Listening/Awake state: Draw the complex mesh pattern as seen in the desktop version.
    - Speaking state: Change color to BUSY (reddish).
- **Settings & Navigation**:
    - Implement Hamburger menu drawer.
    - **Login Options**: Submenu to change PC IP, Port, and Token.
    - **Conversation Options**: Submenu to toggle between "Hold to Speak", "Wake Word", or "Both".
    - **Token Refresh**: Generate a new token and automatically copy it to the clipboard.
- **Persistent Logic**:
    - The setup screen is shown only on the first run.
    - Subsequent launches go straight to the HUD.
    - "Save" actions in settings redirect back to the HUD and reconnect the WebSocket.

## Verification Plan

### Manual Verification
- Deploy to an Android device.
- Verify initial setup screen appears.
- Save credentials and verify it transitions to the HUD.
- Open Hamburger menu and test submenus.
- Verify "Token Refresh" copies a new token.
- Verify "Conversation Options" correctly updates the speech mode.
- Check that the Orb animation changes based on state (Standby vs. Listening).
- Restart the app and verify it opens directly to the HUD.

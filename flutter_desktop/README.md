# MindFlow Desktop

Cross-platform desktop application for MindFlow AI agents, built with Flutter.

## Features

- **Sidebar**: Session management with NEW CHAT, recent sessions list, and user profile
- **InputBar**: Text input with folder selector, model selector, and send button
- **CenterContent**: Empty state with logo and agent-specific suggestion cards
- **WebSocket Integration**: Real-time communication with Python backend
- **Multi-Platform**: Support for Linux, macOS, and Windows

## Project Structure

```
flutter_desktop/
├── lib/
│   ├── main.dart              # App entry point with Provider setup
│   ├── app.dart               # MaterialApp and theme configuration
│   ├── core/
│   │   ├── theme/
│   │   │   ├── app_colors.dart     # Design tokens from Pencil
│   │   │   └── app_typography.dart # Inter & JetBrains Mono fonts
│   │   ├── models/
│   │   │   ├── session.dart        # Chat session model
│   │   │   └── message.dart        # Agent message model
│   │   └── services/
│   │       └── websocket_service.dart # Backend WebSocket connection
│   ├── components/
│   │   ├── sidebar/           # Sidebar components
│   │   │   ├── sidebar.dart
│   │   │   ├── new_chat_button.dart
│   │   │   ├── session_list.dart
│   │   │   └── user_profile.dart
│   │   ├── input/             # InputBar components
│   │   │   ├── input_bar.dart
│   │   │   ├── folder_selector.dart
│   │   │   └── model_selector.dart
│   │   └── chat/              # CenterContent components
│   │       ├── center_content.dart
│   │       └── suggestion_card.dart
│   └── screens/
│       └── chat_screen.dart   # Main screen assembly
├── linux/                     # Linux runner
├── macos/                     # macOS runner
├── windows/                   # Windows runner
└── test/                      # Widget tests
```

## Getting Started

### Prerequisites

- Flutter SDK 3.0.0 or higher
- Dart SDK
- For Linux: GTK development libraries
- For Windows: Visual Studio with C++ workload
- For macOS: Xcode

### Installation

1. **Install Flutter** (if not already installed):
   ```bash
   git clone https://github.com/flutter/flutter.git
   export PATH="$PATH:`pwd`/flutter/bin"
   flutter doctor
   ```

2. **Navigate to the project**:
   ```bash
   cd /home/levybonito/Projetos/MindFlow/flutter_desktop
   ```

3. **Get dependencies**:
   ```bash
   flutter pub get
   ```

### Running the App

#### Linux
```bash
flutter run -d linux
```

#### macOS
```bash
flutter run -d macos
```

#### Windows
```bash
flutter run -d windows
```

### Building for Production

#### Linux
```bash
flutter build linux --release
```

#### macOS
```bash
flutter build macos --release
```

#### Windows
```bash
flutter build windows --release
```

## Configuration

### Backend WebSocket URL

Update the WebSocket URL in `lib/main.dart`:

```dart
WebSocketService(
  backendUrl: 'ws://localhost:8000/ws',  // Change to your backend URL
),
```

### Design Tokens

The app uses design tokens converted from the Pencil design file:

- **Agent Colors**: Orchestrator (#0D6E6E), Coder (#C75D2C), Analyst (#5B6ABF), Researcher (#2D8F5E)
- **Signal Color**: Synapse (#00D4AA) for accents and send button
- **Backgrounds**: Sidebar (#0F0F10), Primary (#121214), Surface (#1A1A1C)
- **Typography**: Inter (UI text), JetBrains Mono (labels, code)

## Testing

Run widget tests:
```bash
flutter test
```

## Design Reference

This implementation is based on the Pencil design file located at:
`/home/levybonito/Projetos/MindFlow/design/mindflow/Frontend/chat-ui.pen`

Key components matched from Pencil:
- **tfW4C / XmbF5**: Sidebar (260px, dark theme)
- **QZ6wU / ir8fB**: InputBar (bottom toolbar + input shell)
- **w0YtT**: CenterContent (logo + suggestions)
- **YBatq**: SuggestionCard (reusable with agent colors)

## Architecture

### State Management
- **Provider**: Used for WebSocket service and application state
- **ChangeNotifier**: WebSocketService manages connection, sessions, and messages

### Communication
- **WebSocket**: Real-time bidirectional communication with Python backend
- **JSON Protocol**: Messages encoded as JSON with type, content, agent, and timestamp

## Troubleshooting

### Font Loading Issues
If fonts don't load correctly, ensure Google Fonts are available or run:
```bash
flutter pub get
```

### WebSocket Connection
If WebSocket fails to connect:
1. Verify backend is running at `ws://localhost:8000/ws`
2. Check firewall settings
3. Update `backendUrl` in `main.dart`

## License

Part of the MindFlow project.

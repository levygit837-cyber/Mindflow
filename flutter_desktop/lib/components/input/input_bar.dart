import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_lucide/flutter_lucide.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/services/websocket_service.dart';
import 'folder_selector.dart';
import 'model_selector.dart';

/// InputBar component - Main user input area
/// 
/// From Pencil: QZ6wU (InputWrap) wrapping ir8fB (InputArea)
/// 
/// Structure:
/// - Toolbar: Folder selector + Model selector (horizontal, gap 8)
/// - Input shell: Text field + Send button (border, padding)
/// - Hint text below input
/// 
/// Layout:
/// - Position: Bottom of screen
/// - Width: fill container (max 1180px)
/// - Gap between elements: 8px
class InputBar extends StatefulWidget {
  const InputBar({super.key});

  @override
  State<InputBar> createState() => _InputBarState();
}

class _InputBarState extends State<InputBar> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onTextChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  void _onTextChanged() {
    setState(() {
      _hasText = _controller.text.isNotEmpty;
    });
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    context.read<WebSocketService>().sendMessage(content: text);
    _controller.clear();
    _focusNode.requestFocus();
  }

  void _handleKeyEvent(KeyEvent event) {
    if (event is KeyDownEvent) {
      if (event.logicalKey == LogicalKeyboardKey.enter &&
          !HardwareKeyboard.instance.isShiftPressed) {
        _sendMessage();
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.bgPrimary,
        border: Border(
          top: BorderSide(color: AppColors.linePrimary),
        ),
      ),
      padding: const EdgeInsets.fromLTRB(32, 16, 32, 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Toolbar: Folder + Model selectors
          _buildToolbar(),
          
          const SizedBox(height: 8),
          
          // Input shell
          _buildInputShell(),
          
          const SizedBox(height: 8),
          
          // Hint text
          _buildHint(),
        ],
      ),
    );
  }

  Widget _buildToolbar() {
    return Row(
      children: [
        const FolderSelector(),
        const SizedBox(width: 8),
        const ModelSelector(),
      ],
    );
  }

  Widget _buildInputShell() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgSurface,
        borderRadius: BorderRadius.circular(12),
      ),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Text input (expanded)
          Expanded(
            child: Material(
              color: Colors.transparent,
              child: KeyboardListener(
                focusNode: FocusNode(),
                onKeyEvent: _handleKeyEvent,
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  style: AppTypography.inputText,
                  decoration: InputDecoration(
                    hintText: 'Pergunte ao MindFlow...',
                    hintStyle: AppTypography.inputHint,
                    border: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    errorBorder: InputBorder.none,
                    focusedErrorBorder: InputBorder.none,
                    disabledBorder: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(vertical: 8),
                    isDense: true,
                  ),
                  maxLines: null,
                  minLines: 1,
                  textInputAction: TextInputAction.newline,
                ),
              ),
            ),
          ),
          
          const SizedBox(width: 12),
          
          // Send button
          _buildSendButton(),
        ],
      ),
    );
  }

  Widget _buildSendButton() {
    final bool canSend = _hasText;
    
    return GestureDetector(
      onTap: canSend ? _sendMessage : null,
      child: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: canSend ? AppColors.signalSynapse : AppColors.linePrimary,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(
          LucideIcons.arrow_up_right,
          size: 15,
          color: canSend ? Colors.white : AppColors.textMeta,
        ),
      ),
    );
  }

  Widget _buildHint() {
    return Text(
      'MindFlow pode cometer erros. Verifique informações importantes.',
      style: AppTypography.inputHintSmall,
      textAlign: TextAlign.center,
    );
  }
}

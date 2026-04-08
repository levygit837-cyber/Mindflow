import 'package:flutter/material.dart';

/// Design tokens converted from Pencil CSS variables
/// Reference: /home/levybonito/Projetos/MindFlow/design/mindflow/Frontend/chat-ui.pen
class AppColors {
  // ============================================
  // AGENT COLORS (from Pencil design tokens)
  // ============================================
  
  /// Orchestrator agent - Teal accent
  /// Used for: NEW CHAT button, active session border, primary actions
  static const agentOrchestrator = Color(0xFF0D6E6E);
  
  /// Coder agent - Orange accent
  /// Used for: Coder suggestion cards, code-related UI
  static const agentCoder = Color(0xFFC75D2C);
  
  /// Analyst agent - Purple/Indigo accent
  /// Used for: Analyst suggestion cards, analysis-related UI
  static const agentAnalyst = Color(0xFF5B6ABF);
  
  /// Researcher agent - Green accent
  /// Used for: Researcher suggestion cards, research-related UI
  static const agentResearcher = Color(0xFF2D8F5E);
  
  // ============================================
  // SIGNAL COLORS
  // ============================================
  
  /// Primary signal/accent color (bright teal)
  /// Used for: Send button, logo, key actions
  static const signalSynapse = Color(0xFF00D4AA);
  
  /// Soft signal color (10% opacity synapse)
  /// Used for: Logo background, subtle highlights
  static const signalSynapseSoft = Color(0x1A00D4AA);
  
  // ============================================
  // BACKGROUND COLORS
  // ============================================
  
  /// Sidebar background - darkest
  static const bgSidebar = Color(0xFF0F0F10);
  
  /// Primary background - main app bg
  static const bgPrimary = Color(0xFF121214);
  
  /// Surface background - cards, inputs
  static const bgSurface = Color(0xFF1A1A1C);
  
  /// Active session background
  static const bgActiveSession = Color(0xFF232326);
  
  // ============================================
  // TEXT COLORS
  // ============================================
  
  /// Primary text - white
  static const textPrimary = Color(0xFFFFFFFF);
  
  /// Secondary text - light gray
  static const textSecondary = Color(0xFFB4B4B7);
  
  /// Meta text - medium gray (labels, hints)
  static const textMeta = Color(0xFF6E6E73);
  
  /// Ghost text - dimmed gray (placeholders)
  static const textGhost = Color(0xFF8A8A8E);
  
  // ============================================
  // LINE/BORDER COLORS
  // ============================================
  
  /// Primary divider/border color
  static const linePrimary = Color(0xFF2A2A2E);
  
  /// Transparent border (for inactive states)
  static const lineTransparent = Color(0x00000000);
  
  // ============================================
  // UTILITY METHODS
  // ============================================
  
  /// Get agent color by type
  static Color getAgentColor(String agentType) {
    switch (agentType.toLowerCase()) {
      case 'orchestrator':
        return agentOrchestrator;
      case 'coder':
        return agentCoder;
      case 'analyst':
        return agentAnalyst;
      case 'researcher':
        return agentResearcher;
      default:
        return agentOrchestrator;
    }
  }
}

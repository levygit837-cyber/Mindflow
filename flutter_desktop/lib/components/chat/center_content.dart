import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/services/websocket_service.dart';
import 'suggestion_card.dart';

/// CenterContent component - Empty state with logo and suggestions
/// 
/// From Pencil: w0YtT (Main Content)
/// 
/// Structure:
/// - Logo section: "M" in circle + title + subtitle
/// - Suggestions: 3 cards in row (Coder, Analyst, Researcher)
/// 
/// Layout:
/// - Vertical layout with gap 32
/// - Centered horizontally
/// - Padding: 0,80 (horizontal)
class CenterContent extends StatelessWidget {
  const CenterContent({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 80),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Logo section
            _buildLogoSection(),
            
            const SizedBox(height: 32),
            
            // Suggestions row
            _buildSuggestions(context),
          ],
        ),
      ),
    );
  }

  Widget _buildLogoSection() {
    return Column(
      children: [
        // Logo circle with "M"
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: AppColors.signalSynapseSoft,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Center(
            child: Text(
              'M',
              style: GoogleFonts.inter(
                fontSize: 36,
                fontWeight: FontWeight.w800,
                color: AppColors.signalSynapse,
              ),
            ),
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Title
        Text(
          'Como posso ajudar?',
          style: AppTypography.headline,
        ),
        
        const SizedBox(height: 8),
        
        // Subtitle
        Text(
          'Selecione uma sugestão ou digite sua pergunta abaixo',
          style: AppTypography.subtitle,
        ),
      ],
    );
  }

  Widget _buildSuggestions(BuildContext context) {
    final suggestions = [
      SuggestionData(
        agent: 'coder',
        label: 'Coder',
        text: 'Implemente autenticação JWT com refresh tokens no backend',
        onTap: () => _sendSuggestion(context, 'Implemente autenticação JWT com refresh tokens no backend'),
      ),
      SuggestionData(
        agent: 'analyst',
        label: 'Analyst',
        text: 'Analise a performance do banco de dados e sugira otimizações',
        onTap: () => _sendSuggestion(context, 'Analise a performance do banco de dados e sugira otimizações'),
      ),
      SuggestionData(
        agent: 'researcher',
        label: 'Researcher',
        text: 'Pesquise as melhores práticas de CI/CD para microserviços',
        onTap: () => _sendSuggestion(context, 'Pesquise as melhores práticas de CI/CD para microserviços'),
      ),
    ];

    return Container(
      constraints: const BoxConstraints(maxWidth: 780),
      child: Column(
        children: suggestions.map((s) => 
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: SuggestionCard(
              agentType: s.agent,
              label: s.label,
              text: s.text,
              onTap: s.onTap,
            ),
          ),
        ).toList(),
      ),
    );
  }

  void _sendSuggestion(BuildContext context, String text) {
    context.read<WebSocketService>().sendMessage(content: text);
  }
}

// Helper class for suggestion data
class SuggestionData {
  final String agent;
  final String label;
  final String text;
  final VoidCallback onTap;

  SuggestionData({
    required this.agent,
    required this.label,
    required this.text,
    required this.onTap,
  });
}

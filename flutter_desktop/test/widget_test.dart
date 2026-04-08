import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mindflow_desktop/app.dart';
import 'package:mindflow_desktop/components/sidebar/sidebar.dart';
import 'package:mindflow_desktop/components/input/input_bar.dart';
import 'package:mindflow_desktop/components/chat/center_content.dart';

void main() {
  group('MindFlow Desktop Widget Tests', () {
    testWidgets('App should render without errors', (WidgetTester tester) async {
      await tester.pumpWidget(const MindFlowApp());
      
      // Wait for the widget to fully load
      await tester.pumpAndSettle();
      
      // Verify the app renders
      expect(find.byType(MaterialApp), findsOneWidget);
    });

    testWidgets('Sidebar should contain NEW CHAT button', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Row(
              children: [
                Sidebar(),
                Expanded(child: SizedBox()),
              ],
            ),
          ),
        ),
      );
      
      await tester.pumpAndSettle();
      
      // Verify NEW CHAT button is present
      expect(find.text('NEW CHAT'), findsOneWidget);
      expect(find.text('MindFlow'), findsOneWidget);
      expect(find.text('RECENT'), findsOneWidget);
    });

    testWidgets('CenterContent should have logo and suggestions', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CenterContent(),
          ),
        ),
      );
      
      await tester.pumpAndSettle();
      
      // Verify logo and text
      expect(find.text('M'), findsOneWidget);
      expect(find.text('Como posso ajudar?'), findsOneWidget);
      expect(find.text('Selecione uma sugestão ou digite sua pergunta abaixo'), findsOneWidget);
      
      // Verify suggestion cards
      expect(find.text('Coder'), findsOneWidget);
      expect(find.text('Analyst'), findsOneWidget);
      expect(find.text('Researcher'), findsOneWidget);
    });

    testWidgets('InputBar should have toolbar and send button', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: InputBar(),
          ),
        ),
      );
      
      await tester.pumpAndSettle();
      
      // Verify toolbar elements
      expect(find.text('folder'), findsOneWidget);
      expect(find.text('claude-4-sonnet'), findsOneWidget);
      
      // Verify hint text
      expect(find.textContaining('MindFlow pode cometer erros'), findsOneWidget);
    });
  });
}

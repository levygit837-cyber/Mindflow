/**
 * ============================================================================
 * 08 - REAL-WORLD SCENARIOS EXAMPLES
 * ============================================================================
 *
 * This file contains comprehensive examples of real-world AI application
 * scenarios. These are practical, production-ready patterns that you'll
 * encounter when building actual AI-powered applications.
 *
 * Topics covered:
 * - Customer support chatbot
 * - Document Q&A system
 * - Content moderation
 * - Email classification and response
 * - Data extraction from documents
 * - Multi-language translation service
 * - Code review assistant
 * - Meeting summarization
 * - Product recommendation system
 * - Sentiment analysis pipeline
 * - Resume/CV parsing
 * - Task automation agent
 *
 * @author OmniMind Team
 * @version 1.0.0
 */

import { ChatOpenAI } from "@langchain/openai";
import {
  HumanMessage,
  AIMessage,
  SystemMessage,
  BaseMessage,
} from "@langchain/core/messages";
import { ChatPromptTemplate, MessagesPlaceholder } from "@langchain/core/prompts";
import { StringOutputParser, JsonOutputParser } from "@langchain/core/output_parsers";
import { RunnableSequence, RunnablePassthrough } from "@langchain/core/runnables";
import { StateGraph, END, START, Annotation, MemorySaver } from "@langchain/langgraph";
import { z } from "zod";
import { createLogger } from "../utils/logger";

const logger = createLogger("RealWorldScenariosExamples");

// ============================================================================
// SECTION 1: CUSTOMER SUPPORT CHATBOT
// ============================================================================

/**
 * Example 1.1: Full-Featured Customer Support Bot
 *
 * A complete customer support chatbot with:
 * - Intent detection
 * - Knowledge base lookup
 * - Ticket creation
 * - Escalation handling
 * - Conversation memory
 */

// Define the support bot state
const CustomerSupportState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (current, update) => [...current, ...update],
    default: () => [],
  }),
  customerInfo: Annotation<{
    id?: string;
    name?: string;
    email?: string;
    tier?: "free" | "pro" | "enterprise";
  }>({
    reducer: (current, update) => ({ ...current, ...update }),
    default: () => ({}),
  }),
  intent: Annotation<string>({
    default: () => "unknown",
  }),
  sentiment: Annotation<"positive" | "neutral" | "negative" | "frustrated">({
    default: () => "neutral",
  }),
  ticketCreated: Annotation<boolean>({
    default: () => false,
  }),
  shouldEscalate: Annotation<boolean>({
    default: () => false,
  }),
  knowledgeBaseResults: Annotation<string[]>({
    default: () => [],
  }),
});

// Simulated knowledge base
const knowledgeBase: Record<string, string[]> = {
  billing: [
    "To update your payment method, go to Settings > Billing > Payment Methods",
    "Invoices are sent on the 1st of each month to your registered email",
    "You can cancel your subscription anytime from Settings > Billing > Cancel",
    "Refunds are processed within 5-7 business days",
  ],
  technical: [
    "Try clearing your browser cache and cookies if you experience loading issues",
    "Our API rate limit is 1000 requests per minute for Pro plans",
    "Check our status page at status.example.com for ongoing incidents",
    "Enable two-factor authentication in Settings > Security > 2FA",
  ],
  account: [
    "To reset your password, click 'Forgot Password' on the login page",
    "You can change your email address in Settings > Profile > Email",
    "To delete your account, contact support with your account verification",
    "Export your data anytime from Settings > Privacy > Export Data",
  ],
  pricing: [
    "Free tier includes 100 API calls per day",
    "Pro plan is $29/month with 10,000 API calls",
    "Enterprise plans start at $299/month with custom limits",
    "Annual billing gives you 2 months free",
  ],
};

// Simulated knowledge base search
function searchKnowledgeBase(query: string, category?: string): string[] {
  const results: string[] = [];
  const searchTerms = query.toLowerCase().split(" ");

  const categoriesToSearch = category
    ? [category]
    : Object.keys(knowledgeBase);

  for (const cat of categoriesToSearch) {
    const articles = knowledgeBase[cat] || [];
    for (const article of articles) {
      const matches = searchTerms.some((term) =>
        article.toLowerCase().includes(term)
      );
      if (matches) {
        results.push(article);
      }
    }
  }

  return results.slice(0, 3);
}

export async function createCustomerSupportBot() {
  logger.info("Creating Customer Support Bot");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0.3,
  });

  const memorySaver = new MemorySaver();

  const graph = new StateGraph(CustomerSupportState)
    // Node 1: Analyze intent and sentiment
    .addNode("analyze", async (state) => {
      const lastMessage = state.messages[state.messages.length - 1];
      const userMessage = lastMessage.content as string;

      const analysisPrompt = ChatPromptTemplate.fromMessages([
        [
          "system",
          `Analyze the customer message and respond with JSON:
           {
             "intent": "billing|technical|account|pricing|complaint|general",
             "sentiment": "positive|neutral|negative|frustrated",
             "urgency": "low|medium|high"
           }`,
        ],
        ["human", "{message}"],
      ]);

      const analysis = await analysisPrompt
        .pipe(model)
        .pipe(new JsonOutputParser())
        .invoke({ message: userMessage });

      // Search knowledge base
      const kbResults = searchKnowledgeBase(userMessage, analysis.intent);

      return {
        intent: analysis.intent,
        sentiment: analysis.sentiment,
        shouldEscalate: analysis.sentiment === "frustrated" || analysis.urgency === "high",
        knowledgeBaseResults: kbResults,
      };
    })

    // Node 2: Generate response
    .addNode("respond", async (state) => {
      const lastMessage = state.messages[state.messages.length - 1];

      let contextInfo = "";
      if (state.knowledgeBaseResults.length > 0) {
        contextInfo = `\n\nRelevant information from our knowledge base:\n${state.knowledgeBaseResults.join("\n")}`;
      }

      const responsePrompt = ChatPromptTemplate.fromMessages([
        [
          "system",
          `You are a helpful customer support agent for a SaaS company.
           Customer tier: ${state.customerInfo.tier || "unknown"}
           Detected intent: ${state.intent}
           Customer sentiment: ${state.sentiment}
           ${contextInfo}

           Guidelines:
           - Be empathetic and professional
           - If frustrated customer, acknowledge their feelings first
           - Provide clear, actionable solutions
           - Offer to escalate to human if needed
           - Keep responses concise but helpful`,
        ],
        new MessagesPlaceholder("history"),
        ["human", "{input}"],
      ]);

      const response = await responsePrompt
        .pipe(model)
        .pipe(new StringOutputParser())
        .invoke({
          history: state.messages.slice(0, -1),
          input: lastMessage.content,
        });

      return {
        messages: [new AIMessage(response)],
      };
    })

    // Node 3: Handle escalation
    .addNode("escalate", async (state) => {
      return {
        messages: [
          new AIMessage(
            "I understand this is frustrating, and I want to make sure you get the best help possible. " +
            "I'm connecting you with a senior support specialist who can assist you further. " +
            "They'll be with you shortly. Is there anything else you'd like me to note for them?"
          ),
        ],
        ticketCreated: true,
      };
    })

    // Define flow
    .addEdge(START, "analyze")
    .addConditionalEdges("analyze", (state) => {
      if (state.shouldEscalate) {
        return "escalate";
      }
      return "respond";
    })
    .addEdge("respond", END)
    .addEdge("escalate", END);

  return graph.compile({ checkpointer: memorySaver });
}

export async function example_1_1_customerSupportBot(): Promise<{
  conversation: Array<{ role: string; content: string }>;
  finalState: {
    intent: string;
    sentiment: string;
    escalated: boolean;
  };
}> {
  logger.info("Example 1.1: Customer Support Bot");

  const bot = await createCustomerSupportBot();
  const threadId = `support-${Date.now()}`;
  const config = { configurable: { thread_id: threadId } };

  const conversation: Array<{ role: string; content: string }> = [];

  // Simulate customer conversation
  const customerMessages = [
    "Hi, I'm having trouble with my billing. I was charged twice this month!",
    "This is really frustrating. I've been a customer for 2 years and this keeps happening!",
  ];

  let finalState: any;

  for (const message of customerMessages) {
    conversation.push({ role: "customer", content: message });

    const result = await bot.invoke(
      {
        messages: [new HumanMessage(message)],
        customerInfo: { tier: "pro", name: "John" },
      },
      config
    );

    finalState = result;
    const lastAiMessage = result.messages[result.messages.length - 1];
    conversation.push({
      role: "agent",
      content: lastAiMessage.content as string,
    });
  }

  return {
    conversation,
    finalState: {
      intent: finalState.intent,
      sentiment: finalState.sentiment,
      escalated: finalState.ticketCreated,
    },
  };
}

// ============================================================================
// SECTION 2: DOCUMENT Q&A SYSTEM
// ============================================================================

/**
 * Example 2.1: Document Question-Answering System
 *
 * Answer questions about documents with:
 * - Source citation
 * - Confidence scoring
 * - Follow-up question handling
 */

interface DocumentChunk {
  content: string;
  source: string;
  page?: number;
  section?: string;
}

interface QAResult {
  answer: string;
  confidence: "high" | "medium" | "low";
  sources: Array<{ source: string; relevance: number }>;
  suggestedFollowUps: string[];
}

export class DocumentQASystem {
  private model: ChatOpenAI;
  private documents: DocumentChunk[] = [];
  private conversationHistory: BaseMessage[] = [];

  constructor() {
    this.model = new ChatOpenAI({
      modelName: "gpt-4-turbo-preview",
      temperature: 0,
    });
  }

  addDocument(chunks: DocumentChunk[]): void {
    this.documents.push(...chunks);
    logger.info("Documents added", { count: chunks.length });
  }

  private findRelevantChunks(query: string, maxChunks: number = 5): DocumentChunk[] {
    // Simplified relevance scoring (in production, use embeddings)
    const queryTerms = query.toLowerCase().split(" ");

    const scored = this.documents.map((doc) => {
      const content = doc.content.toLowerCase();
      const matches = queryTerms.filter((term) => content.includes(term)).length;
      return { doc, score: matches / queryTerms.length };
    });

    return scored
      .sort((a, b) => b.score - a.score)
      .slice(0, maxChunks)
      .filter((s) => s.score > 0.2)
      .map((s) => s.doc);
  }

  async askQuestion(question: string): Promise<QAResult> {
    logger.info("Processing question", { question });

    // Find relevant documents
    const relevantDocs = this.findRelevantChunks(question);

    if (relevantDocs.length === 0) {
      return {
        answer: "I couldn't find relevant information in the documents to answer your question.",
        confidence: "low",
        sources: [],
        suggestedFollowUps: [
          "Could you rephrase your question?",
          "What specific topic are you asking about?",
        ],
      };
    }

    // Format context
    const context = relevantDocs
      .map((doc, i) => `[Source ${i + 1}: ${doc.source}${doc.page ? `, Page ${doc.page}` : ""}]\n${doc.content}`)
      .join("\n\n");

    // Generate answer with citations
    const qaPrompt = ChatPromptTemplate.fromMessages([
      [
        "system",
        `You are a document Q&A assistant. Answer questions based ONLY on the provided context.

         Guidelines:
         - Cite sources using [Source X] notation
         - If information is partial, say so
         - If you can't answer from the context, say "I don't have enough information"
         - Be precise and factual

         Respond in JSON format:
         {
           "answer": "Your detailed answer with [Source X] citations",
           "confidence": "high|medium|low",
           "canFullyAnswer": true|false,
           "suggestedFollowUps": ["question1", "question2"]
         }`,
      ],
      new MessagesPlaceholder("history"),
      [
        "human",
        `Context:\n{context}\n\nQuestion: {question}`,
      ],
    ]);

    const response = await qaPrompt
      .pipe(this.model)
      .pipe(new JsonOutputParser())
      .invoke({
        context,
        question,
        history: this.conversationHistory.slice(-4), // Keep last 2 exchanges
      });

    // Update conversation history
    this.conversationHistory.push(new HumanMessage(question));
    this.conversationHistory.push(new AIMessage(response.answer));

    // Calculate source relevance
    const sources = relevantDocs.map((doc, i) => ({
      source: `${doc.source}${doc.page ? ` (Page ${doc.page})` : ""}`,
      relevance: Math.round((1 - i * 0.15) * 100) / 100,
    }));

    return {
      answer: response.answer,
      confidence: response.confidence,
      sources,
      suggestedFollowUps: response.suggestedFollowUps || [],
    };
  }

  clearHistory(): void {
    this.conversationHistory = [];
  }
}

export async function example_2_1_documentQA(): Promise<{
  question: string;
  result: QAResult;
}> {
  logger.info("Example 2.1: Document Q&A System");

  const qaSystem = new DocumentQASystem();

  // Add sample documents
  qaSystem.addDocument([
    {
      content: `Our company's refund policy allows customers to request a full refund within 30 days
                of purchase. After 30 days, a partial refund of 50% may be granted at management discretion.
                Refunds are processed within 5-7 business days to the original payment method.`,
      source: "Company Policy Manual",
      page: 45,
      section: "Refunds",
    },
    {
      content: `To request a refund, customers should contact support@company.com with their order number
                and reason for the refund. Enterprise customers should contact their dedicated account manager.
                Digital products are non-refundable once downloaded or accessed.`,
      source: "Company Policy Manual",
      page: 46,
      section: "Refund Process",
    },
    {
      content: `Customer support is available Monday through Friday, 9 AM to 6 PM EST.
                Premium support for Enterprise customers is available 24/7.
                Average response time is 4 hours for standard support and 1 hour for premium.`,
      source: "Support SLA Document",
      page: 12,
    },
  ]);

  const question = "What is the refund policy and how do I request one?";
  const result = await qaSystem.askQuestion(question);

  return { question, result };
}

// ============================================================================
// SECTION 3: CONTENT MODERATION SYSTEM
// ============================================================================

/**
 * Example 3.1: AI-Powered Content Moderation
 *
 * Moderate user-generated content with:
 * - Multiple category detection
 * - Severity scoring
 * - Explanation generation
 * - Action recommendations
 */

interface ModerationResult {
  isViolation: boolean;
  categories: Array<{
    category: string;
    detected: boolean;
    severity: "low" | "medium" | "high";
    confidence: number;
  }>;
  overallSeverity: "safe" | "warning" | "violation" | "severe";
  explanation: string;
  recommendedAction: "approve" | "flag_for_review" | "auto_remove" | "ban_user";
  flaggedPhrases: string[];
}

export class ContentModerationSystem {
  private model: ChatOpenAI;
  private moderationCategories = [
    "hate_speech",
    "harassment",
    "violence",
    "sexual_content",
    "spam",
    "misinformation",
    "personal_info",
    "self_harm",
  ];

  constructor() {
    this.model = new ChatOpenAI({
      modelName: "gpt-4-turbo-preview",
      temperature: 0,
    });
  }

  async moderateContent(content: string, context?: {
    platform: string;
    contentType: "post" | "comment" | "message" | "profile";
    userHistory?: { previousViolations: number };
  }): Promise<ModerationResult> {
    logger.info("Moderating content", { length: content.length });

    const moderationPrompt = ChatPromptTemplate.fromMessages([
      [
        "system",
        `You are a content moderation system. Analyze the content for policy violations.

         Categories to check:
         - hate_speech: Content targeting groups based on protected characteristics
         - harassment: Personal attacks, bullying, intimidation
         - violence: Threats, glorification of violence, graphic content
         - sexual_content: Explicit sexual material, inappropriate content
         - spam: Promotional content, repeated messages, scams
         - misinformation: False claims, dangerous health advice
         - personal_info: Sharing private information (doxxing)
         - self_harm: Content promoting self-harm or suicide

         Platform: ${context?.platform || "general"}
         Content Type: ${context?.contentType || "post"}
         User Previous Violations: ${context?.userHistory?.previousViolations || 0}

         Respond with JSON:
         {
           "categories": [
             {"category": "category_name", "detected": true/false, "severity": "low|medium|high", "confidence": 0.0-1.0}
           ],
           "flaggedPhrases": ["phrase1", "phrase2"],
           "explanation": "Brief explanation of findings",
           "overallSeverity": "safe|warning|violation|severe"
         }`,
      ],
      ["human", "Content to moderate:\n\n{content}"],
    ]);

    const analysis = await moderationPrompt
      .pipe(this.model)
      .pipe(new JsonOutputParser())
      .invoke({ content });

    // Determine recommended action
    let recommendedAction: ModerationResult["recommendedAction"] = "approve";
    const violations = analysis.categories.filter((c: any) => c.detected);
    const highSeverity = violations.filter((c: any) => c.severity === "high");

    if (analysis.overallSeverity === "severe") {
      recommendedAction = "ban_user";
    } else if (analysis.overallSeverity === "violation" || highSeverity.length > 0) {
      recommendedAction = "auto_remove";
    } else if (analysis.overallSeverity === "warning") {
      recommendedAction = "flag_for_review";
    }

    // Escalate if user has previous violations
    if (context?.userHistory?.previousViolations && context.userHistory.previousViolations >= 3) {
      if (recommendedAction === "flag_for_review") {
        recommendedAction = "auto_remove";
      } else if (recommendedAction === "auto_remove") {
        recommendedAction = "ban_user";
      }
    }

    return {
      isViolation: violations.length > 0,
      categories: analysis.categories,
      overallSeverity: analysis.overallSeverity,
      explanation: analysis.explanation,
      recommendedAction,
      flaggedPhrases: analysis.flaggedPhrases || [],
    };
  }

  async moderateBatch(contents: string[]): Promise<ModerationResult[]> {
    return Promise.all(contents.map((content) => this.moderateContent(content)));
  }
}

export async function example_3_1_contentModeration(): Promise<{
  content: string;
  result: ModerationResult;
}> {
  logger.info("Example 3.1: Content Moderation");

  const moderator = new ContentModerationSystem();

  // Test with potentially problematic content
  const content = "Check out this amazing investment opportunity! Guaranteed 500% returns in just one week! DM me now!";

  const result = await moderator.moderateContent(content, {
    platform: "social_media",
    contentType: "post",
    userHistory: { previousViolations: 1 },
  });

  return { content, result };
}

// ============================================================================
// SECTION 4: EMAIL CLASSIFICATION AND RESPONSE
// ============================================================================

/**
 * Example 4.1: Intelligent Email Handler
 *
 * Automatically classify, prioritize, and draft responses to emails.
 */

interface EmailClassification {
  category: "support" | "sales" | "billing" | "partnership" | "feedback" | "spam" | "other";
  priority: "low" | "medium" | "high" | "urgent";
  sentiment: "positive" | "neutral" | "negative";
  requiresHumanResponse: boolean;
  suggestedLabels: string[];
  extractedInfo: {
    customerName?: string;
    companyName?: string;
    productMentioned?: string;
    requestType?: string;
    deadline?: string;
  };
}

interface EmailResponse {
  subject: string;
  body: string;
  tone: "formal" | "friendly" | "apologetic";
  suggestedCc?: string[];
  attachmentSuggestions?: string[];
}

export class IntelligentEmailHandler {
  private model: ChatOpenAI;
  private responseTemplates: Record<string, string>;

  constructor() {
    this.model = new ChatOpenAI({
      modelName: "gpt-4-turbo-preview",
      temperature: 0.3,
    });

    this.responseTemplates = {
      support: "Thank you for reaching out to our support team...",
      sales: "Thank you for your interest in our products...",
      billing: "Thank you for contacting us about your billing inquiry...",
      feedback: "We truly appreciate you taking the time to share your feedback...",
    };
  }

  async classifyEmail(email: {
    from: string;
    subject: string;
    body: string;
    attachments?: string[];
  }): Promise<EmailClassification> {
    logger.info("Classifying email", { subject: email.subject });

    const classifyPrompt = ChatPromptTemplate.fromMessages([
      [
        "system",
        `Classify this email and extract relevant information.

         Respond with JSON:
         {
           "category": "support|sales|billing|partnership|feedback|spam|other",
           "priority": "low|medium|high|urgent",
           "sentiment": "positive|neutral|negative",
           "requiresHumanResponse": true/false,
           "suggestedLabels": ["label1", "label2"],
           "extractedInfo": {
             "customerName": "if mentioned",
             "companyName": "if mentioned",
             "productMentioned": "if mentioned",
             "requestType": "type of request",
             "deadline": "if any deadline mentioned"
           }
         }

         Guidelines:
         - Urgent: Security issues, data loss, production outages
         - High: Paying customers, deadlines within 24h
         - Medium: General inquiries, feature requests
         - Low: General feedback, non-time-sensitive`,
      ],
      [
        "human",
        `From: {from}
         Subject: {subject}
         Attachments: {attachments}

         Body:
         {body}`,
      ],
    ]);

    const result = await classifyPrompt
      .pipe(this.model)
      .pipe(new JsonOutputParser())
      .invoke({
        from: email.from,
        subject: email.subject,
        body: email.body,
        attachments: email.attachments?.join(", ") || "none",
      });

    return result as EmailClassification;
  }

  async generateResponse(
    email: { from: string; subject: string; body: string },
    classification: EmailClassification,
    additionalContext?: string
  ): Promise<EmailResponse> {
    logger.info("Generating email response", { category: classification.category });

    const responsePrompt = ChatPromptTemplate.fromMessages([
      [
        "system",
        `Generate a professional email response.

         Classification: ${JSON.stringify(classification)}
         ${additionalContext ? `Additional Context: ${additionalContext}` : ""}

         Guidelines:
         - Match the appropriate tone based on sentiment and category
         - If negative sentiment, be empathetic and apologetic
         - Include specific next steps when possible
         - Keep response concise but thorough
         - Use customer's name if available

         Respond with JSON:
         {
           "subject": "Re: original subject",
           "body": "Full email body",
           "tone": "formal|friendly|apologetic",
           "suggestedCc": ["email addresses to CC if needed"],
           "attachmentSuggestions": ["suggested attachments to include"]
         }`,
      ],
      [
        "human",
        `Original Email:
         From: {from}
         Subject: {subject}
         Body: {body}

         Customer Name: {customerName}
         Request Type: {requestType}`,
      ],
    ]);

    const response = await responsePrompt
      .pipe(this.model)
      .pipe(new JsonOutputParser())
      .invoke({
        from: email.from,
        subject: email.subject,
        body: email.body,
        customerName: classification.extractedInfo.customerName || "Valued Customer",
        requestType: classification.extractedInfo.requestType || "inquiry",
      });

    return response as EmailResponse;
  }
}

export async function example_4_1_emailHandler(): Promise<{
  email: { from: string; subject: string; body: string };
  classification: EmailClassification;
  suggestedResponse: EmailResponse;
}> {
  logger.info("Example 4.1: Email Handler");

  const emailHandler = new IntelligentEmailHandler();

  const email = {
    from: "john.smith@acmecorp.com",
    subject: "Urgent: API Integration Issues",
    body: `Hi Support Team,

I'm John Smith, the lead developer at Acme Corp. We've been using your Enterprise API for the past 6 months, and today we're experiencing critical issues.

Our production system is unable to authenticate with your API - we keep getting 401 errors despite using valid credentials. This is blocking our entire operation, and we have a major product launch scheduled for tomorrow.

We've already tried:
- Regenerating API keys
- Checking our code for errors
- Reviewing your status page (shows all green)

Please help us resolve this ASAP. My direct line is 555-123-4567.

Best regards,
John Smith
Senior Developer, Acme Corp`,
  };

  const classification = await emailHandler.classifyEmail(email);
  const suggestedResponse = await emailHandler.generateResponse(email, classification);

  return { email, classification, suggestedResponse };
}

// ============================================================================
// SECTION 5: CODE REVIEW ASSISTANT
// ============================================================================

/**
 * Example 5.1: AI Code Review System
 *
 * Review code for:
 * - Bugs and potential issues
 * - Performance problems
 * - Security vulnerabilities
 * - Style and best practices
 */

interface CodeReviewResult {
  overallScore: number; // 1-10
  summary: string;
  issues: Array<{
    severity: "critical" | "major" | "minor" | "suggestion";
    category: "bug" | "security" | "performance" | "style" | "maintainability";
    line?: number;
    description: string;
    suggestion: string;
    codeExample?: string;
  }>;
  positives: string[];
  suggestedTests: string[];
}

export class CodeReviewAssistant {
  private model: ChatOpenAI;

  constructor() {
    this.model = new ChatOpenAI({
      modelName: "gpt-4-turbo-preview",
      temperature: 0,
    });
  }

  async reviewCode(
    code: string,
    language: string,
    context?: {
      filename?: string;
      purpose?: string;
      framework?: string;
    }
  ): Promise<CodeReviewResult> {
    logger.info("Reviewing code", { language, lines: code.split("\n").length });

    const reviewPrompt = ChatPromptTemplate.fromMessages([
      [
        "system",
        `You are an expert code reviewer for ${language} code.
         ${context?.framework ? `Framework: ${context.framework}` : ""}
         ${context?.purpose ? `Purpose: ${context.purpose}` : ""}

         Review the code thoroughly for:
         1. Bugs and logic errors
         2. Security vulnerabilities (injection, XSS, etc.)
         3. Performance issues
         4. Code style and best practices
         5. Maintainability and readability

         Respond with JSON:
         {
           "overallScore": 1-10,
           "summary": "Brief overall assessment",
           "issues": [
             {
               "severity": "critical|major|minor|suggestion",
               "category": "bug|security|performance|style|maintainability",
               "line": line_number_or_null,
               "description": "What's wrong",
               "suggestion": "How to fix it",
               "codeExample": "Fixed code example if applicable"
             }
           ],
           "positives": ["Good things about the code"],
           "suggestedTests": ["Test cases that should be added"]
         }`,
      ],
      [
        "human",
        `File: ${context?.filename || "unknown"}

         \`\`\`${language}
         {code}
         \`\`\``,
      ],
    ]);

    const result = await reviewPrompt
      .pipe(this.model)
      .pipe(new JsonOutputParser())
      .invoke({ code });

    return result as CodeReviewResult;
  }

  async suggestRefactoring(
    code: string,
    language: string,
    focusArea?: "performance" | "readability" | "testability"
  ): Promise<{
    refactoredCode: string;
    changes: string[];
    explanation: string;
  }> {

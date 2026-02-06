/**
 * ============================================================================
 * 06 - ADVANCED AI PATTERNS EXAMPLES
 * ============================================================================
 *
 * This file contains comprehensive examples of advanced AI patterns used
 * in production AI systems. These patterns go beyond basic LLM calls and
 * demonstrate sophisticated techniques for building robust AI applications.
 *
 * Topics covered:
 * - RAG (Retrieval-Augmented Generation)
 * - Document loading and splitting
 * - Vector stores and embeddings
 * - Semantic search
 * - Multi-query retrieval
 * - Contextual compression
 * - Self-querying retrieval
 * - Conversation chains with context
 * - Map-reduce patterns
 * - Summarization chains
 * - Question-answering chains
 * - Extraction chains
 * - Routing chains
 * - Fallback chains
 * - Caching patterns
 *
 * @author OmniMind Team
 * @version 1.0.0
 */

import { ChatOpenAI, OpenAIEmbeddings } from "@langchain/openai";
import {
  HumanMessage,
  AIMessage,
  SystemMessage,
  BaseMessage,
} from "@langchain/core/messages";
import {
  ChatPromptTemplate,
  MessagesPlaceholder,
  PromptTemplate,
} from "@langchain/core/prompts";
import { StringOutputParser, JsonOutputParser } from "@langchain/core/output_parsers";
import {
  RunnableSequence,
  RunnablePassthrough,
  RunnableBranch,
  RunnableLambda,
  RunnableMap,
  RunnableParallel,
} from "@langchain/core/runnables";
import { Document } from "@langchain/core/documents";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { MemoryVectorStore } from "langchain/vectorstores/memory";
import { z } from "zod";
import { createLogger } from "../utils/logger";

const logger = createLogger("AdvancedPatternsExamples");

// ============================================================================
// SECTION 1: RAG (RETRIEVAL-AUGMENTED GENERATION)
// ============================================================================

/**
 * Example 1.1: Basic RAG Pipeline
 *
 * RAG combines retrieval of relevant documents with LLM generation.
 * This is the foundation for building knowledge-based AI systems.
 */

// Simulated document store for examples
const sampleDocuments: Document[] = [
  new Document({
    pageContent: `
      TypeScript is a strongly typed programming language that builds on JavaScript.
      It was developed by Microsoft and first released in 2012. TypeScript adds optional
      static typing and class-based object-oriented programming to the language.
      The main benefits include better tooling, error catching at compile time, and
      improved code maintainability for large projects.
    `,
    metadata: { source: "typescript-intro.md", topic: "programming" },
  }),
  new Document({
    pageContent: `
      LangChain is a framework for developing applications powered by language models.
      It provides tools for prompt management, chains, agents, and memory. LangChain
      supports multiple LLM providers including OpenAI, Anthropic, and Cohere.
      Key concepts include: Chains for sequential operations, Agents for autonomous
      decision-making, and Tools for external interactions.
    `,
    metadata: { source: "langchain-docs.md", topic: "ai-frameworks" },
  }),
  new Document({
    pageContent: `
      Vector databases store data as high-dimensional vectors (embeddings). They enable
      semantic search by finding vectors that are mathematically similar. Popular vector
      databases include Pinecone, Weaviate, Milvus, and Chroma. Vector search is essential
      for RAG systems as it allows finding relevant context based on meaning, not just keywords.
    `,
    metadata: { source: "vector-db-guide.md", topic: "databases" },
  }),
  new Document({
    pageContent: `
      Embeddings are numerical representations of text that capture semantic meaning.
      Similar texts have similar embeddings (close in vector space). OpenAI's text-embedding
      models and Sentence Transformers are popular choices. Embedding dimensions typically
      range from 384 to 4096, with higher dimensions capturing more nuance but requiring
      more storage and compute.
    `,
    metadata: { source: "embeddings-explained.md", topic: "ai-fundamentals" },
  }),
  new Document({
    pageContent: `
      Prompt engineering is the practice of designing effective prompts for LLMs.
      Key techniques include: few-shot learning (providing examples), chain-of-thought
      prompting (asking the model to reason step by step), and role-playing (giving
      the model a specific persona). Good prompts are clear, specific, and include
      relevant context.
    `,
    metadata: { source: "prompt-engineering.md", topic: "ai-fundamentals" },
  }),
];

/**
 * Simple in-memory vector store for RAG examples
 */
class SimpleVectorStore {
  private documents: Document[] = [];
  private embeddings: number[][] = [];
  private embeddingModel: OpenAIEmbeddings;

  constructor() {
    this.embeddingModel = new OpenAIEmbeddings({
      modelName: "text-embedding-3-small",
    });
  }

  async addDocuments(docs: Document[]): Promise<void> {
    logger.info("Adding documents to vector store", { count: docs.length });

    const texts = docs.map((doc) => doc.pageContent);
    const newEmbeddings = await this.embeddingModel.embedDocuments(texts);

    this.documents.push(...docs);
    this.embeddings.push(...newEmbeddings);

    logger.info("Documents indexed", { totalDocs: this.documents.length });
  }

  async similaritySearch(query: string, k: number = 3): Promise<Document[]> {
    logger.info("Performing similarity search", { query, k });

    const queryEmbedding = await this.embeddingModel.embedQuery(query);

    // Calculate cosine similarity with all documents
    const similarities = this.embeddings.map((docEmbedding, index) => ({
      index,
      score: this.cosineSimilarity(queryEmbedding, docEmbedding),
    }));

    // Sort by similarity and take top k
    similarities.sort((a, b) => b.score - a.score);
    const topK = similarities.slice(0, k);

    logger.info("Search results", {
      topScores: topK.map((s) => s.score.toFixed(4)),
    });

    return topK.map((s) => this.documents[s.index]);
  }

  private cosineSimilarity(a: number[], b: number[]): number {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  getDocumentCount(): number {
    return this.documents.length;
  }
}

export async function example_1_1_basicRAG(): Promise<{
  query: string;
  retrievedDocs: number;
  answer: string;
}> {
  logger.info("Example 1.1: Basic RAG Pipeline");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  // Create and populate vector store
  const vectorStore = new SimpleVectorStore();
  await vectorStore.addDocuments(sampleDocuments);

  // User query
  const query = "What is LangChain and what are its main components?";

  // Retrieve relevant documents
  const retrievedDocs = await vectorStore.similaritySearch(query, 3);

  // Format context from retrieved documents
  const context = retrievedDocs
    .map((doc, i) => `[Document ${i + 1}]\n${doc.pageContent.trim()}`)
    .join("\n\n");

  // Generate answer using retrieved context
  const prompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      `You are a helpful assistant that answers questions based on the provided context.
       Use only the information from the context to answer. If the context doesn't contain
       relevant information, say so.`,
    ],
    [
      "human",
      `Context:
{context}

Question: {question}

Please provide a comprehensive answer based on the context above.`,
    ],
  ]);

  const chain = prompt.pipe(model).pipe(new StringOutputParser());

  const answer = await chain.invoke({
    context,
    question: query,
  });

  return {
    query,
    retrievedDocs: retrievedDocs.length,
    answer,
  };
}

/**
 * Example 1.2: RAG with Document Chunking
 *
 * Large documents need to be split into smaller chunks for effective retrieval.
 * This example shows how to split documents intelligently.
 */
export async function example_1_2_documentChunking(): Promise<{
  originalLength: number;
  chunks: number;
  avgChunkSize: number;
  sampleChunks: string[];
}> {
  logger.info("Example 1.2: Document Chunking");

  // Long document to split
  const longDocument = `
    # Introduction to Machine Learning

    Machine learning is a subset of artificial intelligence that enables systems to learn
    and improve from experience without being explicitly programmed. It focuses on developing
    algorithms that can access data and use it to learn for themselves.

    ## Types of Machine Learning

    ### Supervised Learning
    In supervised learning, the algorithm learns from labeled training data. The model makes
    predictions based on input features and is corrected when its predictions are wrong.
    Common algorithms include linear regression, decision trees, and neural networks.
    Applications include spam detection, image classification, and price prediction.

    ### Unsupervised Learning
    Unsupervised learning works with unlabeled data. The algorithm tries to find patterns
    and structure in the data without predefined labels. Common techniques include clustering
    (K-means, hierarchical), dimensionality reduction (PCA, t-SNE), and association rules.
    Applications include customer segmentation, anomaly detection, and recommendation systems.

    ### Reinforcement Learning
    Reinforcement learning involves an agent learning to make decisions by performing actions
    in an environment and receiving rewards or penalties. The agent learns to maximize cumulative
    reward over time. Applications include game playing (AlphaGo), robotics, and autonomous vehicles.

    ## The Machine Learning Pipeline

    1. Data Collection: Gathering relevant data from various sources
    2. Data Preprocessing: Cleaning, normalizing, and transforming data
    3. Feature Engineering: Creating and selecting relevant features
    4. Model Selection: Choosing appropriate algorithms
    5. Training: Fitting the model to training data
    6. Evaluation: Assessing model performance on test data
    7. Deployment: Putting the model into production
    8. Monitoring: Tracking model performance over time

    ## Common Challenges

    - Overfitting: Model performs well on training data but poorly on new data
    - Underfitting: Model is too simple to capture underlying patterns
    - Data Quality: Garbage in, garbage out - data must be accurate and relevant
    - Feature Selection: Choosing the right features significantly impacts performance
    - Computational Resources: Large models require significant computing power
  `;

  // Configure the text splitter
  const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: 500, // Target chunk size in characters
    chunkOverlap: 50, // Overlap between chunks to maintain context
    separators: ["\n## ", "\n### ", "\n\n", "\n", " ", ""], // Split hierarchy
  });

  // Split the document
  const chunks = await splitter.createDocuments(
    [longDocument],
    [{ source: "ml-intro.md", author: "OmniMind Team" }] // Metadata for all chunks
  );

  // Calculate statistics
  const chunkSizes = chunks.map((c) => c.pageContent.length);
  const avgChunkSize = Math.round(
    chunkSizes.reduce((a, b) => a + b, 0) / chunks.length
  );

  return {
    originalLength: longDocument.length,
    chunks: chunks.length,
    avgChunkSize,
    sampleChunks: chunks.slice(0, 3).map((c) => c.pageContent.trim().substring(0, 100) + "..."),
  };
}

/**
 * Example 1.3: Multi-Query RAG
 *
 * Generate multiple queries from the user's question to improve retrieval.
 * This helps catch relevant documents that might be missed with a single query.
 */
export async function example_1_3_multiQueryRAG(): Promise<{
  originalQuery: string;
  generatedQueries: string[];
  totalDocsRetrieved: number;
  answer: string;
}> {
  logger.info("Example 1.3: Multi-Query RAG");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0.7,
  });

  const vectorStore = new SimpleVectorStore();
  await vectorStore.addDocuments(sampleDocuments);

  const originalQuery = "How do I build AI applications?";

  // Step 1: Generate multiple query variations
  const queryGeneratorPrompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      `You are a helpful assistant that generates search queries.
       Given a user question, generate 3 different versions of the question
       that might help retrieve relevant information.
       Return only the queries, one per line, no numbering or bullets.`,
    ],
    ["human", "Original question: {question}"],
  ]);

  const queryGenerator = queryGeneratorPrompt.pipe(model).pipe(new StringOutputParser());

  const generatedQueriesRaw = await queryGenerator.invoke({
    question: originalQuery,
  });

  const generatedQueries = [
    originalQuery,
    ...generatedQueriesRaw.split("\n").filter((q) => q.trim()),
  ];

  logger.info("Generated queries", { queries: generatedQueries });

  // Step 2: Retrieve documents for each query
  const allRetrievedDocs: Document[] = [];
  const seenContent = new Set<string>();

  for (const query of generatedQueries) {
    const docs = await vectorStore.similaritySearch(query, 2);
    for (const doc of docs) {
      // Deduplicate by content
      if (!seenContent.has(doc.pageContent)) {
        seenContent.add(doc.pageContent);
        allRetrievedDocs.push(doc);
      }
    }
  }

  // Step 3: Generate answer from combined context
  const context = allRetrievedDocs
    .map((doc, i) => `[Document ${i + 1}]\n${doc.pageContent.trim()}`)
    .join("\n\n");

  const answerPrompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      "You are a helpful assistant. Answer based on the provided context.",
    ],
    [
      "human",
      `Context:\n{context}\n\nQuestion: {question}\n\nProvide a comprehensive answer:`,
    ],
  ]);

  const answer = await answerPrompt
    .pipe(model)
    .pipe(new StringOutputParser())
    .invoke({
      context,
      question: originalQuery,
    });

  return {
    originalQuery,
    generatedQueries,
    totalDocsRetrieved: allRetrievedDocs.length,
    answer,
  };
}

/**
 * Example 1.4: RAG with Reranking
 *
 * After initial retrieval, rerank documents for relevance to improve quality.
 */
export async function example_1_4_ragWithReranking(): Promise<{
  query: string;
  initialDocs: number;
  rerankedDocs: Array<{ content: string; score: number }>;
  answer: string;
}> {
  logger.info("Example 1.4: RAG with Reranking");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const vectorStore = new SimpleVectorStore();
  await vectorStore.addDocuments(sampleDocuments);

  const query = "What are vector databases used for?";

  // Step 1: Initial broad retrieval
  const initialDocs = await vectorStore.similaritySearch(query, 5);

  // Step 2: Rerank using LLM
  const rerankPrompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      `You are a relevance scorer. For each document, score its relevance to the query
       from 0 to 10, where 10 is highly relevant and 0 is not relevant at all.
       Respond with JSON: {"scores": [{"index": 0, "score": X, "reason": "brief reason"}, ...]}`,
    ],
    [
      "human",
      `Query: {query}

Documents:
{documents}

Score each document's relevance:`,
    ],
  ]);

  const documentsFormatted = initialDocs
    .map((doc, i) => `[Document ${i}]\n${doc.pageContent.trim().substring(0, 300)}...`)
    .join("\n\n");

  const rerankResponse = await rerankPrompt
    .pipe(model)
    .pipe(new JsonOutputParser())
    .invoke({
      query,
      documents: documentsFormatted,
    });

  // Sort by score and take top 3
  const scoredDocs = (rerankResponse.scores as Array<{ index: number; score: number }>)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  const rerankedDocs = scoredDocs.map((s) => ({
    content: initialDocs[s.index].pageContent.trim().substring(0, 100) + "...",
    score: s.score,
  }));

  // Step 3: Generate answer from reranked docs
  const topDocs = scoredDocs.map((s) => initialDocs[s.index]);
  const context = topDocs
    .map((doc, i) => `[Document ${i + 1}]\n${doc.pageContent.trim()}`)
    .join("\n\n");

  const answer = await ChatPromptTemplate.fromMessages([
    ["system", "Answer based on the provided context."],
    ["human", `Context:\n{context}\n\nQuestion: {query}`],
  ])
    .pipe(model)
    .pipe(new StringOutputParser())
    .invoke({ context, query });

  return {
    query,
    initialDocs: initialDocs.length,
    rerankedDocs,
    answer,
  };
}

// ============================================================================
// SECTION 2: ADVANCED CHAIN PATTERNS
// ============================================================================

/**
 * Example 2.1: Map-Reduce Chain
 *
 * Process multiple documents in parallel (map) and combine results (reduce).
 * Useful for summarizing multiple documents or aggregating information.
 */
export async function example_2_1_mapReduceChain(): Promise<{
  documentsProcessed: number;
  individualSummaries: string[];
  finalSummary: string;
}> {
  logger.info("Example 2.1: Map-Reduce Chain");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const documents = sampleDocuments.slice(0, 3);

  // Map step: Summarize each document individually
  const mapPrompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a summarizer. Create a 2-sentence summary of the document."],
    ["human", "Document:\n{document}\n\nSummary:"],
  ]);

  const mapChain = mapPrompt.pipe(model).pipe(new StringOutputParser());

  // Process all documents in parallel (map)
  const summaryPromises = documents.map((doc) =>
    mapChain.invoke({ document: doc.pageContent })
  );
  const individualSummaries = await Promise.all(summaryPromises);

  // Reduce step: Combine all summaries into a final summary
  const reducePrompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      `You are a summarizer. Combine the following summaries into a single coherent
       summary that captures the main points from all documents.`,
    ],
    [
      "human",
      `Individual summaries:
{summaries}

Combined summary:`,
    ],
  ]);

  const reduceChain = reducePrompt.pipe(model).pipe(new StringOutputParser());

  const finalSummary = await reduceChain.invoke({
    summaries: individualSummaries
      .map((s, i) => `${i + 1}. ${s}`)
      .join("\n"),
  });

  return {
    documentsProcessed: documents.length,
    individualSummaries,
    finalSummary,
  };
}

/**
 * Example 2.2: Routing Chain
 *
 * Route inputs to different chains based on classification.
 * Useful for handling different types of queries differently.
 */
export async function example_2_2_routingChain(): Promise<{
  input: string;
  detectedRoute: string;
  response: string;
}> {
  logger.info("Example 2.2: Routing Chain");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  // Classification chain
  const classifyPrompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      `Classify the user input into one of these categories:
       - technical: Programming, software, or technical questions
       - general: General knowledge questions
       - creative: Requests for creative content
       Respond with just the category name.`,
    ],
    ["human", "{input}"],
  ]);

  const classifyChain = classifyPrompt.pipe(model).pipe(new StringOutputParser());

  // Specialized chains for each category
  const technicalPrompt = ChatPromptTemplate.fromMessages([
    ["system", "You are an expert programmer. Provide detailed technical answers with code examples when relevant."],
    ["human", "{input}"],
  ]);

  const generalPrompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a knowledgeable assistant. Provide clear and informative answers."],
    ["human", "{input}"],
  ]);

  const creativePrompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a creative writer. Be imaginative and engaging in your responses."],
    ["human", "{input}"],
  ]);

  const technicalChain = technicalPrompt.pipe(model).pipe(new StringOutputParser());
  const generalChain = generalPrompt.pipe(model).pipe(new StringOutputParser());
  const creativeChain = creativePrompt.pipe(model).pipe(new StringOutputParser());

  // Create routing chain
  const routingChain = RunnableBranch.from([
    [
      (x: { input: string; classification: string }) => x.classification.includes("technical"),
      (x: { input: string }) => technicalChain.invoke(x),
    ],
    [
      (x: { input: string; classification: string }) => x.classification.includes("creative"),
      (x: { input: string }) => creativeChain.invoke(x),
    ],
    // Default to general
    (x: { input: string }) => generalChain.invoke(x),
  ]);

  // Test input
  const input = "How do I implement a binary search tree in TypeScript?";

  // Classify first
  const classification = await classifyChain.invoke({ input });

  // Route to appropriate chain
  const response = await routingChain.invoke({ input, classification });

  return {
    input,
    detectedRoute: classification.trim(),
    response,
  };
}

/**
 * Example 2.3: Fallback Chain
 *
 * Automatically fall back to alternative chains when the primary fails.
 */
export async function example_2_3_fallbackChain(): Promise<{
  input: string;
  chainUsed: string;
  response: string;
}> {
  logger.info("Example 2.3: Fallback Chain");

  // Primary model (might fail or be unavailable)
  const primaryModel = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  // Fallback model (more reliable/cheaper)
  const fallbackModel = new ChatOpenAI({
    modelName: "gpt-3.5-turbo",
    temperature: 0,
  });

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a helpful assistant."],
    ["human", "{input}"],
  ]);

  // Create chains
  const primaryChain = prompt.pipe(primaryModel).pipe(new StringOutputParser());
  const fallbackChain = prompt.pipe(fallbackModel).pipe(new StringOutputParser());

  // Chain with fallback
  const chainWithFallback = primaryChain.withFallbacks({
    fallbacks: [fallbackChain],
  });

  const input = "What is the meaning of life?";
  let chainUsed = "primary";

  try {
    const response = await chainWithFallback.invoke({ input });
    return { input, chainUsed, response };
  } catch (error) {
    // If even fallback fails
    chainUsed = "failed";
    return {
      input,
      chainUsed,
      response: "All chains failed to process the request.",
    };
  }
}

/**
 * Example 2.4: Parallel Chain Execution
 *
 * Run multiple chains in parallel and combine their outputs.
 */
export async function example_2_4_parallelChains(): Promise<{
  input: string;
  analysis: {
    sentiment: string;
    topics: string;
    summary: string;
  };
  processingTimeMs: number;
}> {
  logger.info("Example 2.4: Parallel Chain Execution");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const input = `
    The new AI regulation proposal has sparked intense debate in the tech community.
    Supporters argue it will ensure responsible AI development and protect consumer rights.
    Critics worry it could stifle innovation and put companies at a competitive disadvantage.
    Industry leaders are calling for a balanced approach that promotes safety without
    hindering progress. The proposal is expected to be voted on next month.
  `;

  // Define parallel analysis chains
  const sentimentPrompt = ChatPromptTemplate.fromMessages([
    ["system", "Analyze the sentiment. Respond with: positive, negative, or mixed, followed by a brief explanation."],
    ["human", "{input}"],
  ]);

  const topicsPrompt = ChatPromptTemplate.fromMessages([
    ["system", "Extract the main topics/themes. List them comma-separated."],
    ["human", "{input}"],
  ]);

  const summaryPrompt = ChatPromptTemplate.fromMessages([
    ["system", "Provide a one-sentence summary."],
    ["human", "{input}"],
  ]);

  // Create parallel runnable
  const parallelAnalysis = RunnableParallel.from({
    sentiment: sentimentPrompt.pipe(model).pipe(new StringOutputParser()),
    topics: topicsPrompt.pipe(model).pipe(new StringOutputParser()),
    summary: summaryPrompt.pipe(model).pipe(new StringOutputParser()),
  });

  const startTime = Date.now();
  const analysis = await parallelAnalysis.invoke({ input });
  const processingTimeMs = Date.now() - startTime;

  return {
    input: input.trim().substring(0, 100) + "...",
    analysis,
    processingTimeMs,
  };
}

// ============================================================================
// SECTION 3: EXTRACTION AND STRUCTURED OUTPUT
// ============================================================================

/**
 * Example 3.1: Entity Extraction
 *
 * Extract structured entities from unstructured text.
 */
export async function example_3_1_entityExtraction(): Promise<{
  input: string;
  extractedEntities: {
    people: Array<{ name: string; role?: string }>;
    organizations: Array<{ name: string; type?: string }>;
    locations: Array<{ name: string; type?: string }>;
    dates: string[];
    amounts: string[];
  };
}> {
  logger.info("Example 3.1: Entity Extraction");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const input = `
    On March 15, 2024, Tesla CEO Elon Musk announced a $500 million investment
    in a new Gigafactory in Austin, Texas. The facility will employ approximately
    5,000 workers and is expected to be operational by Q4 2025. The announcement
    was made at a press conference attended by Texas Governor Greg Abbott and
    Austin Mayor Kirk Watson. SpaceX, Musk's other company, will also utilize
    part of the facility for rocket component manufacturing.
  `;

  const extractionSchema = z.object({
    people: z.array(z.object({
      name: z.string(),
      role: z.string().optional(),
    })),
    organizations: z.array(z.object({
      name: z.string(),
      type: z.string().optional(),
    })),
    locations: z.array(z.object({
      name: z.string(),
      type: z.string().optional(),
    })),
    dates: z.array(z.string()),
    amounts: z.array(z.string()),
  });

  const structuredModel = model.withStructuredOutput(extractionSchema);

  const prompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      `Extract all entities from the text. Include:
       - People with their roles if mentioned
       - Organizations with their type (company, government, etc.)
       - Locations with their type (city, state, country, etc.)
       - Dates in any format mentioned
       - Monetary amounts or quantities`,
    ],
    ["human", "{input}"],
  ]);

  const chain = prompt.pipe(structuredModel);
  const extractedEntities = await chain.invoke({ input });

  return {
    input: input.trim(),
    extractedEntities,
  };
}

/**
 * Example 3.2: Data Transformation Chain
 *
 * Transform unstructured data into a specific schema.
 */
export async function example_3_2_dataTransformation(): Promise<{
  rawInput: string;
  transformedOutput: {
    productName: string;
    category: string;
    price: number;
    currency: string;
    features: string[];
    availability: "in_stock" | "out_of_stock" | "preorder";
    rating: number | null;
  };
}> {
  logger.info("Example 3.2: Data Transformation");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const rawInput = `
    Check out our amazing new laptop! The TechPro X15 is now available for just
    $1,299.99. It's a high-performance gaming laptop with 32GB RAM, RTX 4080 graphics,
    1TB SSD, and a stunning 15.6" 4K display. Customers love it - rated 4.8 out of 5 stars!
    Currently in stock and shipping within 2 business days.
  `;

  const output

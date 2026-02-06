import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { invokeExampleAgent, streamExampleAgent } from '../../agents/graphs/exampleAgentGraph';
import { createLogger } from '../../utils/logger';

const router = Router();
const logger = createLogger('AgentRoutes');

/**
 * Validation schema for agent request
 */
const agentRequestSchema = z.object({
  message: z.string().min(1, 'Message cannot be empty').max(5000, 'Message too long'),
  options: z
    .object({
      stream: z.boolean().optional().default(false),
      model: z.string().optional(),
      temperature: z.number().min(0).max(2).optional(),
      maxTokens: z.number().int().positive().optional(),
    })
    .optional()
    .default({}),
});

/**
 * Middleware to validate request body
 */
const validateAgentRequest = (req: Request, res: Response, next: NextFunction) => {
  try {
    const validated = agentRequestSchema.parse(req.body);
    req.body = validated;
    next();
  } catch (error) {
    if (error instanceof z.ZodError) {
      return res.status(400).json({
        error: 'Validation Error',
        details: error.errors.map((err) => ({
          path: err.path.join('.'),
          message: err.message,
        })),
      });
    }
    next(error);
  }
};

/**
 * POST /api/agents/chat
 * Main endpoint to interact with the agent
 */
router.post(
  '/chat',
  validateAgentRequest,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { message, options } = req.body;

      logger.info('Received chat request', {
        messageLength: message.length,
        stream: options.stream,
      });

      // Handle streaming response
      if (options.stream) {
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        try {
          for await (const chunk of streamExampleAgent(message)) {
            // Send each chunk as Server-Sent Event
            res.write(`data: ${JSON.stringify(chunk)}\n\n`);
          }
          res.write('data: [DONE]\n\n');
          res.end();
        } catch (error: any) {
          logger.error('Streaming error', { error: error.message });
          res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
          res.end();
        }
        return;
      }

      // Handle regular (non-streaming) response
      const result = await invokeExampleAgent(message);

      // Extract the last AI message
      const lastMessage = result.messages[result.messages.length - 1];

      res.status(200).json({
        success: true,
        response: lastMessage.content,
        metadata: {
          currentStep: result.currentStep,
          context: result.context,
          messageCount: result.messages.length,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * POST /api/agents/invoke
 * Alternative endpoint with more control over agent execution
 */
router.post(
  '/invoke',
  validateAgentRequest,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { message } = req.body;

      logger.info('Invoking agent', { messageLength: message.length });

      const result = await invokeExampleAgent(message);

      res.status(200).json({
        success: true,
        state: {
          messages: result.messages.map((msg) => ({
            type: msg._getType(),
            content: msg.content,
          })),
          currentStep: result.currentStep,
          context: result.context,
          error: result.error,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * GET /api/agents/status
 * Check agent availability and configuration
 */
router.get('/status', (req: Request, res: Response) => {
  logger.info('Agent status check');

  res.status(200).json({
    status: 'operational',
    agents: {
      example: {
        available: true,
        capabilities: ['chat', 'analysis', 'streaming'],
      },
    },
    timestamp: new Date().toISOString(),
  });
});

/**
 * GET /api/agents/models
 * List available models
 */
router.get('/models', (req: Request, res: Response) => {
  res.status(200).json({
    models: [
      {
        id: 'gpt-4-turbo-preview',
        name: 'GPT-4 Turbo',
        provider: 'OpenAI',
        capabilities: ['chat', 'analysis', 'code'],
      },
      {
        id: 'gpt-3.5-turbo',
        name: 'GPT-3.5 Turbo',
        provider: 'OpenAI',
        capabilities: ['chat', 'analysis'],
      },
      {
        id: 'claude-3-opus-20240229',
        name: 'Claude 3 Opus',
        provider: 'Anthropic',
        capabilities: ['chat', 'analysis', 'code', 'vision'],
      },
      {
        id: 'claude-3-sonnet-20240229',
        name: 'Claude 3 Sonnet',
        provider: 'Anthropic',
        capabilities: ['chat', 'analysis', 'code'],
      },
    ],
  });
});

/**
 * POST /api/agents/clear-context
 * Clear agent context/memory (placeholder for future implementation)
 */
router.post('/clear-context', (req: Request, res: Response) => {
  logger.info('Clearing agent context');

  // TODO: Implement context clearing logic
  res.status(200).json({
    success: true,
    message: 'Context cleared successfully',
  });
});

router.post('/invoke', async (req: Request, res: Response, next: NextFunction))
try {
  const { message } = testMessageSchema.parse(req.body);

  logger.info('Test invoke request'), { messageLength: message.length }

  const chatMessage: ChatMessage = {
    id: '1',
    role: 'user',
    content: message,
    timestamp: new Date(),
  };

  const response = await invokeOmniMind([chatMessage]);

  res.status(200).json({
    sucess: true,
    userMessage: message,
    agentResponse: response,
    timestamp: new Date().toISOString(),
  });

} catch (error: any) {
  logger.error('Test invoke failed', { error: error.message });
  next(error);
}

export default router;

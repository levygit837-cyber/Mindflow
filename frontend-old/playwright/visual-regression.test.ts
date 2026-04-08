/**
 * Chat Visualization V2 - Visual Regression Tests
 *
 * Visual regression tests using Playwright to capture and compare
 * screenshots of all V2 components across different themes and states.
 *
 * Task: 25.1 - Setup visual regression testing (optional)
 * Feature: chat-visualization-v2
 *
 * Setup:
 * 1. Install Playwright: npm install -D @playwright/test
 * 2. Install browsers: npx playwright install
 * 3. Run tests: npx playwright test
 * 4. Update snapshots: npx playwright test --update-snapshots
 */

import { test, expect } from '@playwright/test';

// Test configuration for all V2 components
const COMPONENTS = [
  'ThinkingNotifier',
  'ThoughtBlock',
  'DelegationCard',
  'ToolEventCard',
  'StreamNotifier',
  'MemoryRecallCard',
  'AgentTodoList',
  'JourneyTimeline',
  'AgentJourneyPanel',
  'ChatStreamFeed',
];

const THEMES = ['light', 'dark'];

const STATES = {
  ThinkingNotifier: ['active', 'waiting'],
  ThoughtBlock: ['collapsed', 'expanded'],
  DelegationCard: ['simple', 'rich'],
  ToolEventCard: ['running', 'completed', 'error'],
  StreamNotifier: ['accent', 'info', 'success', 'warning', 'error'],
  MemoryRecallCard: ['vector', 'database'],
  AgentTodoList: ['streaming', 'completed'],
  JourneyTimeline: ['live', 'completed'],
  AgentJourneyPanel: ['open', 'closed'],
  ChatStreamFeed: ['streaming', 'history'],
};

/**
 * Visual regression tests for ThinkingNotifier component
 */
test.describe('ThinkingNotifier - Visual Regression', () => {
  test('should render active state correctly in dark theme', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ThinkingNotifier&state=active&theme=dark');
    await expect(page).toHaveScreenshot('ThinkingNotifier-active-dark.png');
  });

  test('should render waiting state correctly in dark theme', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ThinkingNotifier&state=waiting&theme=dark');
    await expect(page).toHaveScreenshot('ThinkingNotifier-waiting-dark.png');
  });

  test('should render active state correctly in light theme', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ThinkingNotifier&state=active&theme=light');
    await expect(page).toHaveScreenshot('ThinkingNotifier-active-light.png');
  });
});

/**
 * Visual regression tests for ThoughtBlock component
 */
test.describe('ThoughtBlock - Visual Regression', () => {
  test('should render collapsed state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ThoughtBlock&state=collapsed&theme=dark');
    await expect(page).toHaveScreenshot('ThoughtBlock-collapsed-dark.png');
  });

  test('should render expanded state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ThoughtBlock&state=expanded&theme=dark');
    await expect(page).toHaveScreenshot('ThoughtBlock-expanded-dark.png');
  });

  test('should render with different agent types', async ({ page }) => {
    const agentTypes = ['orchestrator', 'analyst', 'coder', 'researcher'];
    
    for (const agentType of agentTypes) {
      await page.goto(`/#/chat-visualization-v2?component=ThoughtBlock&agent=${agentType}&theme=dark`);
      await expect(page).toHaveScreenshot(`ThoughtBlock-${agentType}-dark.png`);
    }
  });
});

/**
 * Visual regression tests for DelegationCard component
 */
test.describe('DelegationCard - Visual Regression', () => {
  test('should render simple variant correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=DelegationCard&variant=simple&theme=dark');
    await expect(page).toHaveScreenshot('DelegationCard-simple-dark.png');
  });

  test('should render rich variant correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=DelegationCard&variant=rich&theme=dark');
    await expect(page).toHaveScreenshot('DelegationCard-rich-dark.png');
  });

  test('should render with multiple agents', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=DelegationCard&agents=multi&theme=dark');
    await expect(page).toHaveScreenshot('DelegationCard-multi-agents-dark.png');
  });
});

/**
 * Visual regression tests for ToolEventCard component
 */
test.describe('ToolEventCard - Visual Regression', () => {
  test('should render running state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ToolEventCard&state=running&theme=dark');
    await expect(page).toHaveScreenshot('ToolEventCard-running-dark.png');
  });

  test('should render completed state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ToolEventCard&state=completed&theme=dark');
    await expect(page).toHaveScreenshot('ToolEventCard-completed-dark.png');
  });

  test('should render error state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ToolEventCard&state=error&theme=dark');
    await expect(page).toHaveScreenshot('ToolEventCard-error-dark.png');
  });

  test('should render specialized visualizations', async ({ page }) => {
    const toolTypes = ['read_file', 'shell', 'grep_search'];
    
    for (const toolType of toolTypes) {
      await page.goto(`/#/chat-visualization-v2?component=ToolEventCard&tool=${toolType}&theme=dark`);
      await expect(page).toHaveScreenshot(`ToolEventCard-${toolType}-dark.png`);
    }
  });
});

/**
 * Visual regression tests for StreamNotifier component
 */
test.describe('StreamNotifier - Visual Regression', () => {
  test('should render all tone variants', async ({ page }) => {
    const tones = ['accent', 'info', 'success', 'warning', 'error', 'neutral'];
    
    for (const tone of tones) {
      await page.goto(`/#/chat-visualization-v2?component=StreamNotifier&tone=${tone}&theme=dark`);
      await expect(page).toHaveScreenshot(`StreamNotifier-${tone}-dark.png`);
    }
  });
});

/**
 * Visual regression tests for MemoryRecallCard component
 */
test.describe('MemoryRecallCard - Visual Regression', () => {
  test('should render vector source correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=MemoryRecallCard&source=vector&theme=dark');
    await expect(page).toHaveScreenshot('MemoryRecallCard-vector-dark.png');
  });

  test('should render database source correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=MemoryRecallCard&source=database&theme=dark');
    await expect(page).toHaveScreenshot('MemoryRecallCard-database-dark.png');
  });

  test('should not render in light theme', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=MemoryRecallCard&theme=light');
    await expect(page).toHaveScreenshot('MemoryRecallCard-light-theme-null.png');
  });
});

/**
 * Visual regression tests for AgentTodoList component
 */
test.describe('AgentTodoList - Visual Regression', () => {
  test('should render streaming state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=AgentTodoList&state=streaming&theme=dark');
    await expect(page).toHaveScreenshot('AgentTodoList-streaming-dark.png');
  });

  test('should not render in light theme', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=AgentTodoList&theme=light');
    await expect(page).toHaveScreenshot('AgentTodoList-light-theme-null.png');
  });
});

/**
 * Visual regression tests for JourneyTimeline component
 */
test.describe('JourneyTimeline - Visual Regression', () => {
  test('should render live state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=JourneyTimeline&state=live&theme=dark');
    await expect(page).toHaveScreenshot('JourneyTimeline-live-dark.png');
  });

  test('should render completed state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=JourneyTimeline&state=completed&theme=dark');
    await expect(page).toHaveScreenshot('JourneyTimeline-completed-dark.png');
  });

  test('should render with multiple steps', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=JourneyTimeline&steps=multi&theme=dark');
    await expect(page).toHaveScreenshot('JourneyTimeline-multi-steps-dark.png');
  });
});

/**
 * Visual regression tests for AgentJourneyPanel component
 */
test.describe('AgentJourneyPanel - Visual Regression', () => {
  test('should render open panel correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=AgentJourneyPanel&state=open&theme=dark');
    await expect(page).toHaveScreenshot('AgentJourneyPanel-open-dark.png');
  });

  test('should render with multiple agents side by side', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=AgentJourneyPanel&state=multi&theme=dark');
    await expect(page).toHaveScreenshot('AgentJourneyPanel-multi-panels-dark.png');
  });
});

/**
 * Visual regression tests for ChatStreamFeed component
 */
test.describe('ChatStreamFeed - Visual Regression', () => {
  test('should render streaming state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ChatStreamFeed&state=streaming&theme=dark');
    await expect(page).toHaveScreenshot('ChatStreamFeed-streaming-dark.png');
  });

  test('should render history state correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ChatStreamFeed&state=history&theme=dark');
    await expect(page).toHaveScreenshot('ChatStreamFeed-history-dark.png');
  });

  test('should render with all component types', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ChatStreamFeed&state=complete&theme=dark');
    await expect(page).toHaveScreenshot('ChatStreamFeed-complete-dark.png');
  });

  test('should render complete flow in light theme', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ChatStreamFeed&state=complete&theme=light');
    await expect(page).toHaveScreenshot('ChatStreamFeed-complete-light.png');
  });

  test('should render error states correctly', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ChatStreamFeed&state=error&theme=dark');
    await expect(page).toHaveScreenshot('ChatStreamFeed-error-dark.png');
  });
});

/**
 * Responsive design tests
 */
test.describe('Responsive Design - Visual Regression', () => {
  const viewports = [
    { name: 'mobile', width: 375, height: 667 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'large', width: 1920, height: 1080 },
  ];

  test('should render correctly on different viewports', async ({ page }) => {
    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/#/chat-visualization-v2?component=ChatStreamFeed&state=complete&theme=dark');
      await expect(page).toHaveScreenshot(`ChatStreamFeed-responsive-${viewport.name}-dark.png`);
    }
  });
});

/**
 * Animation tests (capture key frames)
 */
test.describe('Animation States - Visual Regression', () => {
  test('should capture thinking pulse animation', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=ThinkingNotifier&state=active&theme=dark');
    
    // Capture at different animation phases
    await page.waitForTimeout(0);
    await expect(page).toHaveScreenshot('ThinkingNotifier-pulse-0-dark.png');
    
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot('ThinkingNotifier-pulse-500-dark.png');
    
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot('ThinkingNotifier-pulse-1000-dark.png');
  });

  test('should capture panel slide animation', async ({ page }) => {
    await page.goto('/#/chat-visualization-v2?component=AgentJourneyPanel&theme=dark');
    
    // Click to open panel
    await page.click('[data-testid="open-journey-btn"]');
    
    // Capture animation frames
    await page.waitForTimeout(0);
    await expect(page).toHaveScreenshot('AgentJourneyPanel-slide-0-dark.png');
    
    await page.waitForTimeout(100);
    await expect(page).toHaveScreenshot('AgentJourneyPanel-slide-100-dark.png');
    
    await page.waitForTimeout(100);
    await expect(page).toHaveScreenshot('AgentJourneyPanel-slide-200-dark.png');
  });
});

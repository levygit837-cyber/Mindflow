import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for visual regression testing
 * 
 * Task: 25.1 - Setup visual regression testing (optional)
 * Feature: chat-visualization-v2
 *
 * Usage:
 * - Run all tests: npx playwright test
 * - Run with UI: npx playwright test --ui
 * - Update snapshots: npx playwright test --update-snapshots
 * - Run specific file: npx playwright test visual-regression.test.ts
 * - Run specific test: npx playwright test -g "ThoughtBlock"
 */
export default defineConfig({
  // Test directory
  testDir: './playwright',

  // Timeout for each test
  timeout: 30 * 1000,

  // Expect timeout for assertions
  expect: {
    timeout: 5000,
  },

  // Run tests in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
    ['json', { outputFile: 'playwright-results.json' }],
  ],

  // Shared settings for all the projects that use this configuration
  use: {
    // Base URL to use in actions that invoke awaited URLs
    baseURL: 'http://localhost:5173',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Actionability
    actionTimeout: 10000,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Test against mobile viewports
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },

    // Test against branded browsers
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
    },
    {
      name: 'Google Chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    },
  ],

  // Run your local dev server before starting the tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },

  // Output directory for screenshots
  snapshotPathTemplate: '{testDir}/__snapshots__/{testFilePath}/{arg}-{projectName}{ext}',

  // Visual regression specific settings
  // Set pixelmatch threshold (0 = exact, 1 = always pass)
  // Default is 0.2 (20% difference allowed)
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 100,
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    },
  },
});

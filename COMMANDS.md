# 🔧 OmniMind v03 - Command Reference

Quick reference for all commands you'll need during development.

## 📂 Directory Navigation - IMPORTANT!

### Project Structure
```
OmniMindv03/               # Root directory
├── backend/               # Backend workspace
│   ├── package.json      # Backend dependencies & scripts
│   └── src/
├── frontend/             # Frontend workspace (future)
│   └── package.json
└── package.json          # Root orchestrator
```

### Where to Run Commands

**Option 1: From Root Directory** (Recommended)
```bash
# Navigate to project root
cd OmniMindv03

# Run backend commands from root
npm run dev              # Start backend dev server
npm run build            # Build backend
npm run test             # Run backend tests
npm run dev:backend      # Explicit backend dev
npm run dev:frontend     # Start frontend dev (future)
npm run dev:all          # Run both simultaneously
```

**Option 2: From Backend Directory** (Also works)
```bash
# Navigate to backend
cd OmniMindv03/backend

# Run commands directly
npm run dev
npm run build
npm test
npm run lint
```

**Option 3: From Frontend Directory** (Future)
```bash
cd OmniMindv03/frontend
npm run dev
npm run build
```

### Common Mistakes ❌
```bash
# ❌ WRONG - Running backend commands from root WITHOUT workspace flag
cd OmniMindv03
npm run dev              # ❌ Will fail if no root scripts

# ✅ CORRECT - Use root package.json scripts
cd OmniMindv03
npm run dev              # ✅ Now works! Runs backend dev

# ✅ CORRECT - Navigate to backend first
cd OmniMindv03/backend
npm run dev              # ✅ Works!
```

### Quick Start Guide
```bash
# First time setup (from root)
cd OmniMindv03
npm install              # Install root dependencies
npm run install:all      # Install all workspace dependencies

# Daily development (from root)
npm run dev              # Start backend
npm run dev:all          # Start both backend & frontend

# OR navigate to specific workspace
cd backend
npm run dev
```

## 📦 Package Management

### Installing Dependencies
```bash
# Using npm
npm install

# Using yarn
yarn install

# Using pnpm
pnpm install

# Install specific package
npm install <package-name>

# Install as dev dependency
npm install -D <package-name>

# Install globally
npm install -g <package-name>
```

### Updating Dependencies
```bash
# Check for outdated packages
npm outdated

# Update all packages
npm update

# Update specific package
npm update <package-name>

# Update to latest (breaking changes)
npm install <package-name>@latest
```

### Removing Dependencies
```bash
npm uninstall <package-name>
```

## 🚀 Development Commands

### Starting the Server

**From Root Directory:**
```bash
cd OmniMindv03
npm run dev              # Start backend dev server
npm run dev:backend      # Same as above (explicit)
npm run dev:all          # Start backend + frontend together
```

**From Backend Directory:**
```bash
cd OmniMindv03/backend
npm run dev              # Development mode (hot reload)
```

**Production:**
```bash
# From root
npm run build            # Build backend
npm start                # Start production server

# From backend
cd backend
npm run build
npm start

# Watch mode for TypeScript compilation
npm run build -- --watch
```

### Type Checking
```bash
# Check types without building
npm run type-check

# Check types in watch mode
npm run type-check -- --watch
```

## 🧪 Testing Commands

### Running Tests

**From Root Directory:**
```bash
cd OmniMindv03
npm test                 # Run backend tests
npm run test:backend     # Explicit backend tests
npm run test:frontend    # Frontend tests (future)
```

**From Backend Directory:**
```bash
cd OmniMindv03/backend
npm test                 # Run all tests
npm run test:watch       # Run tests in watch mode
npm run test:coverage    # Run tests with coverage
npm test -- path/to/test.spec.ts  # Run specific test file
npm test -- --testNamePattern="should work"  # Run tests matching pattern
npm test -- -u           # Update snapshots
```

### Test Debugging
```bash
# Run tests in debug mode
node --inspect-brk node_modules/.bin/jest --runInBand

# Run single test file in debug mode
node --inspect-brk node_modules/.bin/jest path/to/test.spec.ts
```

## 🔍 Linting & Formatting

### ESLint

**From Root Directory:**
```bash
cd OmniMindv03
npm run lint             # Lint backend
npm run lint:fix         # Lint and fix backend
npm run lint:backend     # Explicit backend lint
```

**From Backend Directory:**
```bash
cd OmniMindv03/backend
npm run lint             # Lint all files
npm run lint:fix         # Lint and fix automatically
npx eslint src/path/to/file.ts  # Lint specific file
npx eslint src/**/*.ts --debug  # Lint and show rules
```

### Prettier

**From Root Directory:**
```bash
cd OmniMindv03
npm run format           # Format backend files
```

**From Backend Directory:**
```bash
cd OmniMindv03/backend
npm run format           # Format all files
npx prettier --check "src/**/*.ts"  # Check formatting without changing
npx prettier --write src/path/to/file.ts  # Format specific file
```

## 🗄️ Database Commands

### Prisma (if using)
```bash
# Generate Prisma client
npx prisma generate

# Create migration
npx prisma migrate dev --name migration-name

# Apply migrations
npx prisma migrate deploy

# Open Prisma Studio
npx prisma studio

# Reset database
npx prisma migrate reset

# Seed database
npx prisma db seed
```

### TypeORM (if using)
```bash
# Run migrations
npm run typeorm migration:run

# Revert migration
npm run typeorm migration:revert

# Create migration
npm run typeorm migration:generate -- -n MigrationName

# Create empty migration
npm run typeorm migration:create -- -n MigrationName
```

### Direct Database Access
```bash
# PostgreSQL
psql -U username -d database_name

# MongoDB
mongo

# SQLite
sqlite3 database.db
```

## 🔐 Environment Setup

### Managing .env Files
```bash
# Copy example env file
cp env.example .env

# Edit env file (Linux/Mac)
nano .env
vim .env

# Edit env file (Windows)
notepad .env
code .env
```

### Validate Environment
```bash
# Check if required env vars are set
node -e "require('dotenv').config(); console.log(process.env.OPENAI_API_KEY ? '✓ API key set' : '✗ API key missing')"
```

## 📝 Git Commands

### Basic Git Workflow
```bash
# Check status
git status

# Stage changes
git add .
git add src/path/to/file.ts

# Commit changes
git commit -m "feat: add new feature"

# Push changes
git push origin main

# Pull latest changes
git pull origin main
```

### Branch Management
```bash
# Create new branch
git checkout -b feature/your-feature-name

# Switch branches
git checkout branch-name

# List branches
git branch

# Delete branch
git branch -d branch-name

# Merge branch
git merge branch-name
```

### Stashing Changes
```bash
# Stash changes
git stash

# List stashes
git stash list

# Apply stash
git stash apply

# Pop stash (apply and remove)
git stash pop
```

## 🐳 Docker Commands (Future)

```bash
# Build image
docker build -t omnimind-backend .

# Run container
docker run -p 8000:8000 omnimind-backend

# Run with environment variables
docker run -p 8000:8000 --env-file .env omnimind-backend

# Stop container
docker stop <container-id>

# View logs
docker logs <container-id>

# Docker compose
docker-compose up
docker-compose down
docker-compose logs -f
```

## 🔄 Process Management

### Using PM2 (Production)
```bash
# Install PM2
npm install -g pm2

# Start app
pm2 start dist/index.js --name omnimind

# List processes
pm2 list

# Monitor
pm2 monit

# Logs
pm2 logs omnimind

# Restart
pm2 restart omnimind

# Stop
pm2 stop omnimind

# Delete
pm2 delete omnimind

# Save process list
pm2 save

# Startup script
pm2 startup
```

## 📊 Monitoring & Debugging

### View Logs
```bash
# View application logs (if using file logging)
tail -f logs/combined.log
tail -f logs/error.log

# View with grep
tail -f logs/combined.log | grep ERROR
```

### Performance Testing
```bash
# Install Apache Bench
# Linux: sudo apt-get install apache2-utils
# Mac: (already installed)

# Test endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# Load test with POST
ab -n 100 -c 10 -p data.json -T application/json http://localhost:8000/api/agents/chat
```

### Memory & CPU Monitoring
```bash
# Node.js memory usage
node --expose-gc --inspect dist/index.js

# Monitor with htop (Linux/Mac)
htop

# Monitor with Task Manager (Windows)
# Press Ctrl+Shift+Esc
```

## 🔧 Utility Commands

### TypeScript Compilation
```bash
# Compile once
npx tsc

# Watch mode
npx tsc --watch

# Check for errors only
npx tsc --noEmit

# Generate declaration files
npx tsc --declaration
```

### Node Version Management
```bash
# Using nvm (Node Version Manager)
nvm install 18
nvm use 18
nvm list
nvm alias default 18

# Check current version
node --version
npm --version
```

### Clean & Reset
```bash
# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear npm cache
npm cache clean --force

# Remove build artifacts
rm -rf dist

# Full reset
rm -rf node_modules dist package-lock.json && npm install
```

## 🌐 Network & API Testing

### cURL Commands
```bash
# GET request
curl http://localhost:8000/health

# POST request with JSON
curl -X POST http://localhost:8000/api/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# POST with file
curl -X POST http://localhost:8000/api/upload \
  -F "file=@path/to/file.txt"

# With authentication
curl -X GET http://localhost:8000/api/protected \
  -H "Authorization: Bearer YOUR_TOKEN"

# Save response to file
curl http://localhost:8000/api/data > response.json

# Verbose output
curl -v http://localhost:8000/health
```

### HTTPie (Alternative to cURL)
```bash
# Install
npm install -g httpie

# GET request
http GET localhost:8000/health

# POST request
http POST localhost:8000/api/agents/chat message="Hello"

# With headers
http POST localhost:8000/api/agents/chat \
  Authorization:"Bearer TOKEN" \
  message="Hello"
```

## 📦 Build & Deploy

### Production Build
```bash
# Build
npm run build

# Test build locally
NODE_ENV=production node dist/index.js

# Build with source maps
tsc --sourceMap
```

### Deploy Commands (Examples)
```bash
# Vercel
vercel deploy
vercel --prod

# Railway
railway up
railway logs

# Heroku
git push heroku main
heroku logs --tail

# AWS (with AWS CLI)
aws s3 sync ./dist s3://your-bucket-name
```

## 🔍 Troubleshooting Commands

### Port Issues
```bash
# Check what's using port 8000 (Linux/Mac)
lsof -i :8000

# Kill process on port (Linux/Mac)
kill -9 $(lsof -t -i:8000)

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Permission Issues
```bash
# Fix npm permissions (Linux/Mac)
sudo chown -R $USER ~/.npm
sudo chown -R $USER /usr/local/lib/node_modules

# Windows (Run as Administrator)
# Right-click Command Prompt > Run as Administrator
```

### Module Resolution Issues
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear TypeScript cache
rm -rf dist
rm -rf node_modules/.cache
```

## 📚 Documentation Generation

### JSDoc
```bash
# Generate documentation
npx jsdoc -c jsdoc.json

# With better-docs theme
npm install -D better-docs
npx jsdoc -c jsdoc.json -t node_modules/better-docs
```

### TypeDoc
```bash
# Install
npm install -D typedoc

# Generate docs
npx typedoc src/index.ts

# With custom config
npx typedoc --options typedoc.json
```

## ⚡ Quick Shortcuts

### One-Liners

**From Root Directory:**
```bash
# First time setup
cd OmniMindv03 && npm install && npm run install:all

# Install, setup env, and start
cd OmniMindv03 && cp backend/env.example backend/.env && npm run dev

# Build and start production
cd OmniMindv03 && npm run build && npm start

# Lint, test, and build
cd OmniMindv03 && npm run lint && npm run test && npm run build

# Full reset
cd OmniMindv03 && npm run reset && npm run install:all
```

**From Backend Directory:**
```bash
# Install, setup env, and start
cd OmniMindv03/backend && npm install && cp env.example .env && npm run dev

# Clean install
cd OmniMindv03/backend && rm -rf node_modules package-lock.json && npm install && npm run dev

# Build and start production
cd OmniMindv03/backend && npm run build && npm start

# Lint, test, and build
cd OmniMindv03/backend && npm run lint && npm test && npm run build

# Full reset and start fresh
cd OmniMindv03/backend && rm -rf node_modules dist logs && npm install && npm run dev
```

### Aliases (Add to .bashrc or .zshrc)
```bash
# For root directory
alias om="cd ~/OmniMindv03"  # Adjust path to your project
alias omdev="cd ~/OmniMindv03 && npm run dev"
alias ombuild="cd ~/OmniMindv03 && npm run build"

# For backend directory
alias ombe="cd ~/OmniMindv03/backend"
alias nrd="npm run dev"
alias nrb="npm run build"
alias nrt="npm test"
alias nrl="npm run lint"
alias nrf="npm run format"
alias nrs="npm start"
alias ni="npm install"
alias nrm="rm -rf node_modules package-lock.json"
```

---

## 💡 Tips

1. **Use npm scripts**: Defined in `package.json`, standardizes commands across team
2. **Watch mode**: Use `--watch` flags for faster development
3. **Verbose output**: Add `--verbose` or `-v` flags when debugging
4. **Dry run**: Many commands support `--dry-run` to see what would happen
5. **Help**: Add `--help` to any command to see available options

## 📖 Command Help

```bash
# NPM help
npm help

# Package help
npm help <command>

# TypeScript compiler options
npx tsc --help

# Node.js help
node --help
```

---

**Pro Tip**: Create a `Makefile` or custom npm scripts for commonly used command combinations!

Example `package.json` scripts:
```json
{
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "lint": "eslint src/**/*.ts",
    "lint:fix": "eslint src/**/*.ts --fix",
    "format": "prettier --write \"src/**/*.ts\"",
    "type-check": "tsc --noEmit",
    "clean": "rm -rf dist node_modules",
    "reset": "npm run clean && npm install",
    "prebuild": "npm run lint && npm run type-check",
    "postbuild": "echo 'Build complete!'",
    "deploy": "npm run build && npm start"
  }
}
```

import winston from 'winston';
import path from 'path';

// Define log levels
const levels = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4,
};

// Define log colors
const colors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  http: 'magenta',
  debug: 'blue',
};

// Tell winston about our colors
winston.addColors(colors);

// Determine log level based on environment
const level = () => {
  const env = process.env.NODE_ENV || 'development';
  const isDevelopment = env === 'development';
  return isDevelopment ? 'debug' : process.env.LOG_LEVEL || 'info';
};

// Define format for logs
const format = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss:ms' }),
  winston.format.colorize({ all: true }),
  winston.format.printf(
    (info) => `${info.timestamp} [${info.level}] ${info.message} ${
      info.metadata && Object.keys(info.metadata).length
        ? JSON.stringify(info.metadata, null, 2)
        : ''
    }`
  )
);

// Define format for file logs (without colors)
const fileFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss:ms' }),
  winston.format.uncolorize(),
  winston.format.printf(
    (info) => `${info.timestamp} [${info.level}] ${info.message} ${
      info.metadata && Object.keys(info.metadata).length
        ? JSON.stringify(info.metadata)
        : ''
    }`
  )
);

// Define transports
const transports = [
  // Console transport
  new winston.transports.Console({
    format: format,
  }),
];

// Add file transports in production
if (process.env.NODE_ENV === 'production') {
  transports.push(
    new winston.transports.File({
      filename: path.join('logs', 'error.log'),
      level: 'error',
      format: fileFormat,
    }),
    new winston.transports.File({
      filename: path.join('logs', 'combined.log'),
      format: fileFormat,
    })
  );
}

// Create the logger
const logger = winston.createLogger({
  level: level(),
  levels,
  transports,
  exitOnError: false,
});

// Create a logger factory that allows creating loggers with context
export const createLogger = (context: string) => {
  return {
    error: (message: string, metadata?: any) => {
      logger.error(`[${context}] ${message}`, { metadata });
    },
    warn: (message: string, metadata?: any) => {
      logger.warn(`[${context}] ${message}`, { metadata });
    },
    info: (message: string, metadata?: any) => {
      logger.info(`[${context}] ${message}`, { metadata });
    },
    http: (message: string, metadata?: any) => {
      logger.http(`[${context}] ${message}`, { metadata });
    },
    debug: (message: string, metadata?: any) => {
      logger.debug(`[${context}] ${message}`, { metadata });
    },
  };
};

export default logger;

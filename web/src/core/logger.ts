/**
 * Logging utility for Code Cartographer
 *
 * Usage:
 *   import { logger } from '@/core/logger';
 *   logger.debug('Component rendered', { nodeCount: 10 });
 *   logger.info('Graph loaded successfully');
 *   logger.warn('Deprecated feature used');
 *   logger.error('Failed to fetch data', error);
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogConfig {
  level: LogLevel;
  enabled: boolean;
  timestamp: boolean;
}

class Logger {
  private config: LogConfig = {
    level: import.meta.env.DEV ? 'debug' : 'warn',
    enabled: true,
    timestamp: import.meta.env.DEV,
  };

  private shouldLog(level: LogLevel): boolean {
    if (!this.config.enabled) return false;

    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error'];
    const currentLevelIndex = levels.indexOf(this.config.level);
    const messageLevelIndex = levels.indexOf(level);

    return messageLevelIndex >= currentLevelIndex;
  }

  private formatMessage(level: LogLevel, message: string, ...args: any[]): string {
    const timestamp = this.config.timestamp ? `[${new Date().toISOString()}] ` : '';
    const levelStr = `[${level.toUpperCase()}]`;
    return `${timestamp}${levelStr} ${message}`;
  }

  debug(message: string, ...args: any[]): void {
    if (this.shouldLog('debug')) {
      console.log(this.formatMessage('debug', message), ...args);
    }
  }

  info(message: string, ...args: any[]): void {
    if (this.shouldLog('info')) {
      console.info(this.formatMessage('info', message), ...args);
    }
  }

  warn(message: string, ...args: any[]): void {
    if (this.shouldLog('warn')) {
      console.warn(this.formatMessage('warn', message), ...args);
    }
  }

  error(message: string, ...args: any[]): void {
    if (this.shouldLog('error')) {
      console.error(this.formatMessage('error', message), ...args);
    }
  }

  /**
   * Configure logger behavior
   */
  configure(config: Partial<LogConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Temporarily disable logging
   */
  disable(): void {
    this.config.enabled = false;
  }

  /**
   * Re-enable logging
   */
  enable(): void {
    this.config.enabled = true;
  }
}

export const logger = new Logger();

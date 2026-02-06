import config from '@/config/index';
import { ChatDeepSeek } from '@langchain/deepseek';
import { agent } from '@/config';
import winston from 'winston/lib/winston/config';

try {
  const omni = new ChatDeepSeek({
    model: agent.defaultModel,
    temperature: agent.defaultTemperature,
  });
} catch {
  winston;
}

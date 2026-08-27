/**
 * Model Settings Persistence
 * Manages storage and retrieval of per-agent model selections and conversation model preferences
 */

export const AGENT_NAMES = ['router', 'planning', 'retrieval', 'tools_registry', 'research_specialist', 'coding_specialist', 'synthesizer', 'critic'] as const;
export type AgentName = typeof AGENT_NAMES[number];

const AGENT_MODELS_STORAGE_KEY = 'agent-model-settings';
const CONVERSATION_MODEL_STORAGE_KEY = 'conversation-model';
const AVAILABLE_MODELS_STORAGE_KEY = 'available-models';
const MODEL_DETECTION_TIMES_STORAGE_KEY = 'model-detection-times';

export interface AgentModelSettings {
    [key: string]: string | undefined;
}

export interface ModelDetectionTimes {
    [modelName: string]: string;
}

/**
 * Get display name for an agent (capitalize first letter)
 */
export function getAgentDisplayName(agent: string): string {
    return agent.charAt(0).toUpperCase() + agent.slice(1);
}

/**
 * Load all per-agent model selections from localStorage
 */
export function loadAgentModels(): AgentModelSettings {
    if (typeof window === 'undefined') return {};
    try {
        const stored = window.localStorage.getItem(AGENT_MODELS_STORAGE_KEY);
        return stored ? JSON.parse(stored) : {};
    } catch (error) {
        console.warn('Failed to load agent models from localStorage:', error);
        return {};
    }
}

/**
 * Save all per-agent model selections to localStorage
 */
export function saveAgentModels(settings: AgentModelSettings): void {
    if (typeof window === 'undefined') return;
    try {
        window.localStorage.setItem(AGENT_MODELS_STORAGE_KEY, JSON.stringify(settings));
    } catch (error) {
        console.warn('Failed to save agent models to localStorage:', error);
    }
}

/**
 * Load the conversation-level model selection from localStorage
 */
export function loadConversationModel(): string | undefined {
    if (typeof window === 'undefined') return undefined;
    try {
        const stored = window.localStorage.getItem(CONVERSATION_MODEL_STORAGE_KEY);
        return stored || undefined;
    } catch (error) {
        console.warn('Failed to load conversation model from localStorage:', error);
        return undefined;
    }
}

/**
 * Save the conversation-level model selection to localStorage
 */
export function saveConversationModel(model: string | undefined): void {
    if (typeof window === 'undefined') return;
    try {
        if (model) {
            window.localStorage.setItem(CONVERSATION_MODEL_STORAGE_KEY, model);
        } else {
            window.localStorage.removeItem(CONVERSATION_MODEL_STORAGE_KEY);
        }
    } catch (error) {
        console.warn('Failed to save conversation model to localStorage:', error);
    }
}

/**
 * Load the list of available models from localStorage
 */
export function loadAvailableModels(): string[] {
    if (typeof window === 'undefined') return [];
    try {
        const stored = window.localStorage.getItem(AVAILABLE_MODELS_STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.warn('Failed to load available models from localStorage:', error);
        return [];
    }
}

/**
 * Save the list of available models to localStorage
 */
export function saveAvailableModels(models: string[]): void {
    if (typeof window === 'undefined') return;
    try {
        window.localStorage.setItem(AVAILABLE_MODELS_STORAGE_KEY, JSON.stringify(models));
    } catch (error) {
        console.warn('Failed to save available models to localStorage:', error);
    }
}

/**
 * Load model detection timestamps from localStorage
 */
export function loadModelDetectionTimes(): ModelDetectionTimes {
    if (typeof window === 'undefined') return {};
    try {
        const stored = window.localStorage.getItem(MODEL_DETECTION_TIMES_STORAGE_KEY);
        return stored ? JSON.parse(stored) : {};
    } catch (error) {
        console.warn('Failed to load model detection times from localStorage:', error);
        return {};
    }
}

/**
 * Save model detection timestamps to localStorage
 */
export function saveModelDetectionTimes(times: ModelDetectionTimes): void {
    if (typeof window === 'undefined') return;
    try {
        window.localStorage.setItem(MODEL_DETECTION_TIMES_STORAGE_KEY, JSON.stringify(times));
    } catch (error) {
        console.warn('Failed to save model detection times to localStorage:', error);
    }
}

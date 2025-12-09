/**
 * Mandate Storage Utilities
 *
 * Persistent storage for AP2 mandates across agent runs.
 * Uses JSON file similar to Python implementation.
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Storage file path (in parent directory)
const MANDATE_STORAGE_FILE = join(__dirname, '..', '.agentgatepay_mandates.json');

export interface StoredMandate {
  mandate_token: string;
  budget_usd: number;
  budget_remaining: number;
  purpose?: string;
  created_at?: string;
  [key: string]: any;
}

interface MandateStorage {
  [agentId: string]: StoredMandate;
}

/**
 * Load all mandates from storage file
 */
function loadMandates(): MandateStorage {
  if (!existsSync(MANDATE_STORAGE_FILE)) {
    return {};
  }

  try {
    const data = readFileSync(MANDATE_STORAGE_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('⚠️  Failed to load mandates:', error);
    return {};
  }
}

/**
 * Save all mandates to storage file
 */
function saveMandates(mandates: MandateStorage): void {
  try {
    writeFileSync(MANDATE_STORAGE_FILE, JSON.stringify(mandates, null, 2));
  } catch (error) {
    console.error('⚠️  Failed to save mandates:', error);
  }
}

/**
 * Save a mandate for an agent
 */
export function saveMandate(agentId: string, mandate: StoredMandate): void {
  const mandates = loadMandates();
  mandates[agentId] = {
    ...mandate,
    created_at: mandate.created_at || new Date().toISOString()
  };
  saveMandates(mandates);
}

/**
 * Get a mandate for an agent
 */
export function getMandate(agentId: string): StoredMandate | null {
  const mandates = loadMandates();
  return mandates[agentId] || null;
}

/**
 * Clear a mandate for an agent
 */
export function clearMandate(agentId: string): void {
  const mandates = loadMandates();
  delete mandates[agentId];
  saveMandates(mandates);
}

/**
 * Clear all mandates
 */
export function clearAllMandates(): void {
  saveMandates({});
}

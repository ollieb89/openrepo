import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import {
  ensureDirectory,
  safeReadDir,
  safeReadFile,
  pathExists,
  isWritable,
  initializeWorkspace,
  getWorkspaceHealth,
  FilesystemError,
} from '../../src/lib/filesystem-utils';

describe('Filesystem Utils', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'openclaw-test-'));
  });

  afterEach(async () => {
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  describe('ensureDirectory', () => {
    it('should create directory if it does not exist', async () => {
      const testPath = path.join(tempDir, 'new-dir');
      const result = await ensureDirectory(testPath);

      expect(result.success).toBe(true);
      expect(result.error).toBeUndefined();

      const exists = await pathExists(testPath);
      expect(exists).toBe(true);
    });

    it('should create nested directories recursively', async () => {
      const testPath = path.join(tempDir, 'a', 'b', 'c', 'd');
      const result = await ensureDirectory(testPath);

      expect(result.success).toBe(true);
      const exists = await pathExists(testPath);
      expect(exists).toBe(true);
    });

    it('should return success if directory already exists', async () => {
      const testPath = path.join(tempDir, 'existing');
      await fs.mkdir(testPath);

      const result = await ensureDirectory(testPath);
      expect(result.success).toBe(true);
    });

    it('should be idempotent when called concurrently', async () => {
      const testPath = path.join(tempDir, 'concurrent');

      const results = await Promise.all([
        ensureDirectory(testPath),
        ensureDirectory(testPath),
        ensureDirectory(testPath),
        ensureDirectory(testPath),
        ensureDirectory(testPath),
      ]);

      expect(results.every((r) => r.success)).toBe(true);
      const exists = await pathExists(testPath);
      expect(exists).toBe(true);
    });

    it('should handle paths with special characters', async () => {
      const testPath = path.join(tempDir, 'special chars @#$');
      const result = await ensureDirectory(testPath);

      expect(result.success).toBe(true);
    });
  });

  describe('safeReadDir', () => {
    it('should read directory contents successfully', async () => {
      const testPath = path.join(tempDir, 'read-test');
      await fs.mkdir(testPath);
      await fs.writeFile(path.join(testPath, 'file1.txt'), 'content');
      await fs.writeFile(path.join(testPath, 'file2.txt'), 'content');
      await fs.mkdir(path.join(testPath, 'subdir'));

      const result = await safeReadDir(testPath);

      expect(result.success).toBe(true);
      expect(result.entries).toBeDefined();
      expect(result.entries?.length).toBe(3);
    });

    it('should return error when directory does not exist', async () => {
      const testPath = path.join(tempDir, 'nonexistent');
      const result = await safeReadDir(testPath);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('ENOENT');
      expect(result.entries).toBeUndefined();
    });

    it('should return error when path is a file not directory', async () => {
      const testPath = path.join(tempDir, 'file.txt');
      await fs.writeFile(testPath, 'content');

      const result = await safeReadDir(testPath);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('ENOTDIR');
    });

    it('should handle empty directory', async () => {
      const testPath = path.join(tempDir, 'empty');
      await fs.mkdir(testPath);

      const result = await safeReadDir(testPath);

      expect(result.success).toBe(true);
      expect(result.entries?.length).toBe(0);
    });
  });

  describe('safeReadFile', () => {
    it('should read file contents successfully', async () => {
      const testPath = path.join(tempDir, 'test.txt');
      const content = 'Hello, World!';
      await fs.writeFile(testPath, content);

      const result = await safeReadFile(testPath);

      expect(result.success).toBe(true);
      expect(result.content).toBe(content);
    });

    it('should return error when file does not exist', async () => {
      const testPath = path.join(tempDir, 'nonexistent.txt');
      const result = await safeReadFile(testPath);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('ENOENT');
    });

    it('should handle empty file', async () => {
      const testPath = path.join(tempDir, 'empty.txt');
      await fs.writeFile(testPath, '');

      const result = await safeReadFile(testPath);

      expect(result.success).toBe(true);
      expect(result.content).toBe('');
    });

    it('should handle large files', async () => {
      const testPath = path.join(tempDir, 'large.txt');
      const largeContent = 'x'.repeat(10000);
      await fs.writeFile(testPath, largeContent);

      const result = await safeReadFile(testPath);

      expect(result.success).toBe(true);
      expect(result.content?.length).toBe(10000);
    });
  });

  describe('pathExists', () => {
    it('should return true for existing directory', async () => {
      const exists = await pathExists(tempDir);
      expect(exists).toBe(true);
    });

    it('should return true for existing file', async () => {
      const testPath = path.join(tempDir, 'exists.txt');
      await fs.writeFile(testPath, 'content');

      const exists = await pathExists(testPath);
      expect(exists).toBe(true);
    });

    it('should return false for nonexistent path', async () => {
      const testPath = path.join(tempDir, 'nonexistent');
      const exists = await pathExists(testPath);
      expect(exists).toBe(false);
    });
  });

  describe('initializeWorkspace', () => {
    it('should create all required directories', async () => {
      const workspaceRoot = path.join(tempDir, 'workspace');
      const result = await initializeWorkspace(workspaceRoot);

      expect(result.success).toBe(true);

      const checks = [
        await pathExists(workspaceRoot),
        await pathExists(path.join(workspaceRoot, 'projects')),
        await pathExists(path.join(workspaceRoot, 'workspace')),
        await pathExists(path.join(workspaceRoot, 'workspace', '.openclaw')),
        await pathExists(path.join(workspaceRoot, 'agents')),
      ];

      expect(checks.every(Boolean)).toBe(true);
    });

    it('should succeed when workspace already exists', async () => {
      const workspaceRoot = path.join(tempDir, 'existing-workspace');
      await initializeWorkspace(workspaceRoot);

      const result = await initializeWorkspace(workspaceRoot);
      expect(result.success).toBe(true);
    });
  });

  describe('getWorkspaceHealth', () => {
    it('should return healthy for fully initialized workspace', async () => {
      const workspaceRoot = path.join(tempDir, 'healthy-workspace');
      await initializeWorkspace(workspaceRoot);

      const health = await getWorkspaceHealth(workspaceRoot);

      expect(health.healthy).toBe(true);
      expect(health.checks.root).toBe(true);
      expect(health.checks.rootWritable).toBe(true);
      expect(health.checks.projects).toBe(true);
      expect(health.checks.workspace).toBe(true);
      expect(health.checks.agents).toBe(true);
    });

    it('should return unhealthy for missing directories', async () => {
      const workspaceRoot = path.join(tempDir, 'incomplete-workspace');
      await fs.mkdir(workspaceRoot);

      const health = await getWorkspaceHealth(workspaceRoot);

      expect(health.healthy).toBe(false);
      expect(health.checks.root).toBe(true);
      expect(health.checks.projects).toBe(false);
    });

    it('should return unhealthy for nonexistent workspace', async () => {
      const workspaceRoot = path.join(tempDir, 'nonexistent');
      const health = await getWorkspaceHealth(workspaceRoot);

      expect(health.healthy).toBe(false);
      expect(health.checks.root).toBe(false);
    });
  });

  describe('FilesystemError', () => {
    it('should create error with all properties', () => {
      const err = new FilesystemError('Test error', 'ETEST', '/test/path');

      expect(err.name).toBe('FilesystemError');
      expect(err.message).toBe('Test error');
      expect(err.code).toBe('ETEST');
      expect(err.filePath).toBe('/test/path');
    });

    it('should include original error if provided', () => {
      const original = new Error('Original error');
      const err = new FilesystemError('Test error', 'ETEST', '/test/path', original);

      expect(err.originalError).toBe(original);
    });
  });
});

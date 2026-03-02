import fs from 'fs/promises';
import fsSync from 'fs';
import path from 'path';
import { Dirent } from 'fs';

export class FilesystemError extends Error {
  constructor(
    message: string,
    public code: string,
    public filePath: string,
    public originalError?: unknown
  ) {
    super(message);
    this.name = 'FilesystemError';
  }
}

export interface EnsureDirectoryResult {
  success: boolean;
  error?: FilesystemError;
}

export interface SafeReadDirResult {
  success: boolean;
  entries?: Dirent[];
  error?: FilesystemError;
}

export interface SafeReadFileResult {
  success: boolean;
  content?: string;
  error?: FilesystemError;
}

/**
 * Ensures directory exists with proper error handling.
 * Handles: missing directories, permission errors, concurrent creation
 */
export async function ensureDirectory(
  dirPath: string,
  options: { permissions?: number } = {}
): Promise<EnsureDirectoryResult> {
  try {
    // Validate path (basic security check)
    const normalized = path.normalize(dirPath);
    if (normalized.includes('..') && !normalized.startsWith(process.cwd())) {
      return {
        success: false,
        error: new FilesystemError(
          'Invalid path: path traversal detected',
          'EINVALID',
          dirPath
        ),
      };
    }

    // Try to create directory (recursive handles missing parents)
    await fs.mkdir(normalized, { recursive: true, mode: options.permissions });
    return { success: true };
  } catch (err: unknown) {
    const error = err as NodeJS.ErrnoException;
    
    // Directory already exists - this is success
    if (error.code === 'EEXIST') {
      return { success: true };
    }

    // Permission denied
    if (error.code === 'EACCES') {
      return {
        success: false,
        error: new FilesystemError(
          `Permission denied: Cannot create directory at ${dirPath}. Check file permissions.`,
          'EACCES',
          dirPath,
          error
        ),
      };
    }

    // No space left
    if (error.code === 'ENOSPC') {
      return {
        success: false,
        error: new FilesystemError(
          `No space left on device for ${dirPath}`,
          'ENOSPC',
          dirPath,
          error
        ),
      };
    }

    // Read-only filesystem
    if (error.code === 'EROFS') {
      return {
        success: false,
        error: new FilesystemError(
          `Read-only filesystem: Cannot create ${dirPath}`,
          'EROFS',
          dirPath,
          error
        ),
      };
    }

    // Generic error
    return {
      success: false,
      error: new FilesystemError(
        `Failed to create directory: ${error.message || 'Unknown error'}`,
        error.code || 'UNKNOWN',
        dirPath,
        error
      ),
    };
  }
}

/**
 * Safely reads directory with existence check.
 * Returns empty array if directory doesn't exist instead of throwing.
 */
export async function safeReadDir(dirPath: string): Promise<SafeReadDirResult> {
  try {
    // Check if directory exists first
    const stats = await fs.stat(dirPath);
    
    if (!stats.isDirectory()) {
      return {
        success: false,
        error: new FilesystemError(
          `Path exists but is not a directory: ${dirPath}`,
          'ENOTDIR',
          dirPath
        ),
      };
    }

    const entries = await fs.readdir(dirPath, { withFileTypes: true });
    return { success: true, entries };
  } catch (err: unknown) {
    const error = err as NodeJS.ErrnoException;

    // Directory doesn't exist - return empty instead of error
    if (error.code === 'ENOENT') {
      return {
        success: false,
        error: new FilesystemError(
          `Directory does not exist: ${dirPath}`,
          'ENOENT',
          dirPath,
          error
        ),
      };
    }

    // Permission denied
    if (error.code === 'EACCES') {
      return {
        success: false,
        error: new FilesystemError(
          `Permission denied: Cannot read directory ${dirPath}`,
          'EACCES',
          dirPath,
          error
        ),
      };
    }

    return {
      success: false,
      error: new FilesystemError(
        `Failed to read directory: ${error.message || 'Unknown error'}`,
        error.code || 'UNKNOWN',
        dirPath,
        error
      ),
    };
  }
}

/**
 * Safely reads file with existence and permission checks.
 */
export async function safeReadFile(
  filePath: string,
  encoding: BufferEncoding = 'utf-8'
): Promise<SafeReadFileResult> {
  try {
    const content = await fs.readFile(filePath, encoding);
    return { success: true, content };
  } catch (err: unknown) {
    const error = err as NodeJS.ErrnoException;

    if (error.code === 'ENOENT') {
      return {
        success: false,
        error: new FilesystemError(
          `File does not exist: ${filePath}`,
          'ENOENT',
          filePath,
          error
        ),
      };
    }

    if (error.code === 'EACCES') {
      return {
        success: false,
        error: new FilesystemError(
          `Permission denied: Cannot read file ${filePath}`,
          'EACCES',
          filePath,
          error
        ),
      };
    }

    return {
      success: false,
      error: new FilesystemError(
        `Failed to read file: ${error.message || 'Unknown error'}`,
        error.code || 'UNKNOWN',
        filePath,
        error
      ),
    };
  }
}

/**
 * Checks if path exists and is accessible.
 */
export async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Checks if path is writable.
 */
export async function isWritable(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath, fsSync.constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validates and initializes OpenClaw workspace structure.
 */
export async function initializeWorkspace(root: string): Promise<EnsureDirectoryResult> {
  const requiredDirs = [
    root,
    path.join(root, 'projects'),
    path.join(root, 'workspace'),
    path.join(root, 'workspace', '.openclaw'),
    path.join(root, 'agents'),
  ];

  for (const dir of requiredDirs) {
    const result = await ensureDirectory(dir);
    if (!result.success) {
      return result;
    }
  }

  return { success: true };
}

/**
 * Gets workspace health status.
 */
export async function getWorkspaceHealth(root: string) {
  const checks = {
    root: await pathExists(root),
    rootWritable: await isWritable(root),
    projects: await pathExists(path.join(root, 'projects')),
    workspace: await pathExists(path.join(root, 'workspace')),
    agents: await pathExists(path.join(root, 'agents')),
  };

  return {
    healthy: Object.values(checks).every(Boolean),
    checks,
  };
}

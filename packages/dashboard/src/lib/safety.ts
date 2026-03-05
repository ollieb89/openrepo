import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const UNLOCK_COOKIE_NAME = 'oc_edit_unlocked';
const UNLOCK_DURATION_MS = 30 * 60 * 1000; // 30 minutes

export enum WriteMode {
    ReadOnly = 'readonly',
    Staging = 'staging',
    AutoApply = 'autoapply',
}

export function getWriteMode(): WriteMode {
    const mode = process.env.DASHBOARD_WRITE_MODE || 'staging';
    if (Object.values(WriteMode).includes(mode as WriteMode)) {
        return mode as WriteMode;
    }
    return WriteMode.Staging;
}

export async function isUnlocked(): Promise<boolean> {
    if (getWriteMode() === WriteMode.ReadOnly) {
        return false;
    }

    const cookieStore = await cookies();
    const unlockCookie = cookieStore.get(UNLOCK_COOKIE_NAME);

    if (!unlockCookie) {
        return false;
    }

    try {
        const expiresAt = parseInt(unlockCookie.value, 10);
        return Date.now() < expiresAt;
    } catch {
        return false;
    }
}

export async function setUnlockState(unlocked: boolean): Promise<void> {
    const cookieStore = await cookies();
    if (unlocked) {
        const expiresAt = Date.now() + UNLOCK_DURATION_MS;
        cookieStore.set(UNLOCK_COOKIE_NAME, expiresAt.toString(), {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: UNLOCK_DURATION_MS / 1000,
            path: '/',
        });
    } else {
        cookieStore.delete(UNLOCK_COOKIE_NAME);
    }
}

/**
 * Middleware wrapper for write-mode enforcement.
 */
export function withWriteLock(handler: (req: any, ...args: any[]) => Promise<NextResponse>) {
    return async (req: any, ...args: any[]) => {
        const mode = getWriteMode();

        if (mode === WriteMode.ReadOnly) {
            return NextResponse.json(
                { error: 'Forbidden', message: 'Dashboard is in read-only mode' },
                { status: 403 }
            );
        }

        if (!(await isUnlocked())) {
            return NextResponse.json(
                { error: 'Unauthorized', message: 'Editing is locked. Please unlock it in the UI.' },
                { status: 401 }
            );
        }

        return handler(req, ...args);
    };
}

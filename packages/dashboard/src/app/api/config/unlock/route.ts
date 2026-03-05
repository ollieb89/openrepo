import { NextRequest, NextResponse } from 'next/server';
import { isUnlocked, setUnlockState, getWriteMode, WriteMode } from '@/lib/safety';
import { withAuth } from '@/lib/auth-middleware';

async function getHandler(request: NextRequest): Promise<NextResponse> {
    return NextResponse.json({
        unlocked: await isUnlocked(),
        writeMode: getWriteMode(),
    });
}

async function postHandler(request: NextRequest): Promise<NextResponse> {
    const mode = getWriteMode();
    if (mode === WriteMode.ReadOnly) {
        return NextResponse.json(
            { error: 'Forbidden', message: 'Dashboard is in read-only mode' },
            { status: 403 }
        );
    }

    try {
        const body = await request.json();
        const { unlocked } = body;

        await setUnlockState(!!unlocked);

        return NextResponse.json({
            unlocked: !!unlocked,
            writeMode: mode,
        });
    } catch (error) {
        return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
    }
}

export const GET = withAuth(getHandler);
export const POST = withAuth(postHandler);

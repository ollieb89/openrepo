import { NextRequest, NextResponse } from 'next/server';
import { findRippleEffects } from '@/lib/sync/graph';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json(
      { error: 'Missing id parameter' },
      { status: 400 }
    );
  }

  try {
    const effects = findRippleEffects(id);
    
    return NextResponse.json({
      id,
      effects,
      count: effects.length
    });
  } catch (error: any) {
    console.error('Ripple effects API error:', error);
    return NextResponse.json(
      { error: 'Internal server error', message: error.message },
      { status: 500 }
    );
  }
}

/**
 * Next.js API Route: Local Model Deck Generation
 * Integrates with Gemma 3 4B model running on localhost:8000
 */

import { NextRequest, NextResponse } from 'next/server';
import { checkLocalModelStatus, generateDeckWithLocalModel, buildDeckWithLocalModel } from '@/lib/localModel';

export async function POST(request: NextRequest) {
  try {
    // Check if local model is available
    const isAvailable = await checkLocalModelStatus();
    if (!isAvailable) {
      return NextResponse.json(
        {
          error: 'Local model not available',
          message: 'The local Gemma 3 4B model is not running. Please start it with: python3 scripts/active/pipeline/api-server.py',
        },
        { status: 503 }
      );
    }

    // Parse request body
    const body = await request.json();
    const { commander, theme, colors, powerLevel, useCollectionOnly, userCollection } = body;

    // Validate required fields
    if (!theme || !colors || !powerLevel) {
      return NextResponse.json(
        { error: 'Missing required fields: theme, colors, powerLevel' },
        { status: 400 }
      );
    }

    // Generate deck structure with local model
    const result = await buildDeckWithLocalModel({
      commander,
      theme,
      colors,
      powerLevel,
      useCollectionOnly,
      userCollection,
    });

    // Return the structured deck plan
    // Note: This is the JSON structure, not the final 100-card deck
    // The frontend would need to call execute-deck-structure.ts separately
    // or we build the full integration
    return NextResponse.json({
      success: true,
      structure: result.structure,
      generationTime: result.generationTime,
      modelUsed: 'gemma-3-4b-local',
      note: 'This is the deck structure. For full 100-card deck, use the executor endpoint.',
    });

  } catch (error: any) {
    console.error('Local model generation error:', error);
    
    return NextResponse.json(
      {
        error: 'Deck generation failed',
        message: error.message || 'Unknown error occurred',
      },
      { status: 500 }
    );
  }
}

// Health check endpoint
export async function GET() {
  const isAvailable = await checkLocalModelStatus();
  
  return NextResponse.json({
    available: isAvailable,
    model: 'gemma-3-4b-local',
    endpoint: 'http://localhost:8000',
    status: isAvailable ? 'online' : 'offline',
  });
}

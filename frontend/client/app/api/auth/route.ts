import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');

    if (!code) {
      return NextResponse.json({ error: 'Code is required' }, { status: 400 });
    }

    const response = await axios.post('https://www.strava.com/oauth/token', {
      client_id: process.env.NEXT_PUBLIC_STRAVA_CLIENT_ID,
      client_secret: process.env.STRAVA_CLIENT_SECRET,
      code: code,
      grant_type: 'authorization_code',
    });

    const { access_token } = response.data;
    return NextResponse.json({ access_token });
  } catch (error) {
    console.error('Error exchanging code for token:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
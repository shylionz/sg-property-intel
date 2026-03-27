import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Fetch data from the backend API
    const response = await fetch('http://localhost:8000/dashboard');
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    return NextResponse.json({ error: 'Failed to fetch dashboard data from backend' }, { status: 500 });
  }
}
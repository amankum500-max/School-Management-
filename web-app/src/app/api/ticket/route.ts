import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';
import speakeasy from 'speakeasy';

const prisma = new PrismaClient();

// 1. Generate Dynamic Secure QR (TOTP)
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const ticketNo = searchParams.get('ticketNo');

  const ticket = await prisma.hallTicket.findUnique({
    where: { ticketNo: ticketNo! },
    include: { student: true }
  });

  if (!ticket) return NextResponse.json({ error: "Ticket not found" }, { status: 404 });

  // TOTP Generation (Changes every 30 seconds)
  const token = speakeasy.totp({
    secret: ticket.student.totpSecret!,
    encoding: 'base32'
  });

  // QR Payload (Encrypted format)
  const qrPayload = JSON.stringify({ t: ticket.ticketNo, c: token, s: ticket.student.id });

  return NextResponse.json({ qrPayload });
}

import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';
import speakeasy from 'speakeasy';

const prisma = new PrismaClient();

export async function POST(req: Request) {
  const { ticketNo, token } = await req.json();

  const ticket = await prisma.hallTicket.findUnique({
    where: { ticketNo },
    include: { student: true, examCenter: true }
  });

  if (!ticket) return NextResponse.json({ status: "FAKE_TICKET" });

  // 1. Verify TOTP (Anti-Screenshot Check)
  const isValidTOTP = speakeasy.totp.verify({
    secret: ticket.student.totpSecret!,
    encoding: 'base32',
    token: token,
    window: 1 // 30 sec tolerance
  });

  if (!isValidTOTP) {
    return NextResponse.json({ status: "EXPIRED_QR", message: "QR Code has expired or is fake." });
  }

  // 2. Return Full Profile & Routing for the UI
  return NextResponse.json({
    status: "SUCCESS",
    profile: {
      name: ticket.student.name,
      photo: ticket.student.photoUrl,
      attendance: ticket.student.attendance,
      feeStatus: ticket.student.feeStatus,
      route: {
        lat: ticket.examCenter?.lat,
        lng: ticket.examCenter?.lng,
        room: ticket.examCenter?.roomNo,
        seat: ticket.examCenter?.seatNo
      }
    }
  });
}

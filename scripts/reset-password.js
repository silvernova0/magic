const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function resetPassword() {
  const email = process.argv[2] || 'silvernova0@gmail.com';
  const newPassword = process.argv[3] || 'admin123';

  try {
    // Check if user exists
    const user = await prisma.user.findUnique({
      where: { email },
    });

    if (!user) {
      console.log('❌ User with email', email, 'not found!');
      process.exit(1);
    }

    // Hash new password
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    // Update user's password and set role to ADMIN
    const updated = await prisma.user.update({
      where: { email },
      data: {
        password: hashedPassword,
        role: 'ADMIN',
      },
    });

    console.log('✅ Password reset successfully!');
    console.log('');
    console.log('📧 Email:', updated.email);
    console.log('🔑 New Password:', newPassword);
    console.log('👤 Name:', updated.name);
    console.log('🛡️  Role:', updated.role);
    console.log('');
    console.log('You can now login at http://localhost:3002/login');
  } catch (error) {
    console.error('❌ Error resetting password:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

console.log('🔐 Resetting password...');
console.log('');
resetPassword();

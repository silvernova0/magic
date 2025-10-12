const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function createAdmin() {
  const email = process.argv[2] || 'admin@example.com';
  const password = process.argv[3] || 'admin123';
  const name = process.argv[4] || 'Admin';

  try {
    // Check if user already exists
    const existing = await prisma.user.findUnique({
      where: { email },
    });

    if (existing) {
      console.log('❌ User with this email already exists!');
      console.log('   Use Prisma Studio to change their role to ADMIN:');
      console.log('   npx prisma studio');
      process.exit(1);
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Create admin user
    const admin = await prisma.user.create({
      data: {
        name,
        email,
        password: hashedPassword,
        role: 'ADMIN',
      },
    });

    console.log('✅ Admin user created successfully!');
    console.log('');
    console.log('📧 Email:', admin.email);
    console.log('🔑 Password:', password);
    console.log('👤 Name:', admin.name);
    console.log('🛡️  Role: ADMIN');
    console.log('');
    console.log('You can now login at http://localhost:3000/login');
  } catch (error) {
    console.error('❌ Error creating admin:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

console.log('🚀 Creating admin user...');
console.log('');
createAdmin();

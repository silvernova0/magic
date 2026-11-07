# Registration & Role-Based Access Guide

## ✅ What's Been Set Up

Your Magic: The Gathering deck builder now has:

1. **Registration System** - New users can create accounts
2. **Password Security** - Passwords are hashed with bcrypt
3. **Role-Based Access** - Users can be either USER or ADMIN
4. **Admin Dashboard** - Admins can manage users and promote/demote roles

## 🚀 How to Get Started

### For New Users:

1. **Visit the app**: http://localhost:3000
2. **Click "Create one"** on the login page (or go to http://localhost:3000/register)
3. **Fill in the registration form**:
   - Name: Your display name
   - Email: Your email address
   - Password: At least 6 characters
   - Confirm Password: Must match
4. **Click "Create Account"**
5. **You'll be redirected to login** - sign in with your new credentials

### Creating Your First Admin User:

Since all new users are created as "USER" role by default, you need to manually promote the first admin. Here's how:

**Option 1: Using Prisma Studio (Recommended)**
```pwsh
npx prisma studio
```
- This opens a web interface at http://localhost:5555
- Click on "User" table
- Find your user and click to edit
- Change `role` from "USER" to "ADMIN"
- Save

**Option 2: Using SQL directly**
```pwsh
# Open the database
sqlite3 prisma/dev.db

# Find your user ID
SELECT id, email, role FROM User;

# Promote to admin (replace YOUR_USER_ID)
UPDATE User SET role = 'ADMIN' WHERE id = 'YOUR_USER_ID';

# Exit
.exit
```

**Option 3: Create via API (temporary dev script)**
Create a file `scripts/create-admin.js`:
```javascript
const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function createAdmin() {
  const email = 'admin@example.com';
  const password = await bcrypt.hash('admin123', 10);
  
  const admin = await prisma.user.create({
    data: {
      name: 'Admin',
      email: email,
      password: password,
      role: 'ADMIN',
    },
  });
  
  console.log('Admin created:', admin.email);
  await prisma.$disconnect();
}

createAdmin();
```

Then run:
```pwsh
node scripts/create-admin.js
```

## 🔑 Default Test Accounts

After creating your first admin using one of the methods above, you can:

1. **Sign in as admin**
2. **Go to http://localhost:3000/admin**
3. **Promote other users to admin** using the admin panel

## 👤 User Roles

### USER Role (Default)
- Can manage their own card collection
- Can create and save decks
- Can import cards
- Can use commander search

### ADMIN Role
- Everything a USER can do, plus:
- Access to `/admin` dashboard
- View all users and their stats
- Promote users to ADMIN
- Demote ADMINs to USER
- See "Admin" badge in sidebar

## 📝 Pages & Routes

### Public Pages:
- `/login` - Sign in page
- `/register` - New user registration

### Protected Pages (Require Login):
- `/` - Home dashboard with your decks
- `/collection` - Your card collection
- `/import` - Import cards from CSV or decklist
- `/commander` - Commander deck search
- `/deckbuilder` - Build new decks
- `/decks` - View your saved decks

### Admin Only:
- `/admin` - User management dashboard

## 🔒 Security Features

1. **Password Hashing**: All passwords are hashed with bcrypt (10 rounds)
2. **Session Management**: JWT-based sessions with NextAuth
3. **Route Protection**: Middleware automatically redirects unauthorized users
4. **Role Verification**: Admin routes check role server-side
5. **SQL Injection Prevention**: Prisma ORM with parameterized queries

## 🎯 Testing the System

### Test User Registration:
1. Go to http://localhost:3000/register
2. Create user: `user1@test.com` / `password123`
3. Login at http://localhost:3000/login
4. Add some cards to collection

### Test Admin Functions:
1. Promote `user1@test.com` to admin (using one of the methods above)
2. Sign out and sign back in
3. You should see "Admin" badge in sidebar
4. Click "Admin Panel" button
5. Create another user: `user2@test.com`
6. As admin, you can promote/demote `user2@test.com`

### Test Multi-User Isolation:
1. As `user1`, add cards to collection
2. Sign out
3. Login as `user2`
4. Collection should be empty (data is per-user)

## 🛠️ Database Schema

```prisma
model User {
  id            String    @id @default(cuid())
  name          String?
  email         String?   @unique
  password      String?              // Hashed with bcrypt
  role          UserRole  @default(USER)  // USER or ADMIN
  emailVerified DateTime?
  image         String?
  createdAt     DateTime  @default(now())
  accounts      Account[]
  sessions      Session[]
  decks         Deck[]
  cards         UserCard[]
}

enum UserRole {
  USER
  ADMIN
}
```

## 📊 Admin Dashboard Features

The admin panel at `/admin` shows:
- Total number of registered users
- User details (name, email, role)
- User statistics (card count, deck count)
- Join date for each user
- Promote/Demote buttons

## 🔄 Migration Applied

A new database migration was applied: `20251012130831_add_password_and_role`

This added:
- `password` field (String, nullable)
- `role` field (UserRole enum, default USER)
- `createdAt` field (DateTime)

## 🚨 Important Notes

### For Development:
- The app is currently set to auto-create the first user as USER role
- You must manually promote the first admin
- Consider adding an environment variable for initial admin email

### For Production:
Before deploying, consider:
1. Add email verification
2. Implement password reset functionality
3. Add rate limiting on login/registration
4. Set up proper session expiration
5. Use environment variables for admin configuration
6. Implement 2FA for admin accounts
7. Add audit logging for admin actions

## 🎉 Ready to Use!

The dev server is running at http://localhost:3000

Try it out:
1. Register a new account
2. Promote yourself to admin (using Prisma Studio)
3. Explore the admin panel
4. Create more users and manage their roles!

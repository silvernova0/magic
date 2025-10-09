import { prisma } from "./prisma";

export async function getDefaultUser() {
  const user = await prisma.user.findUnique({
    where: {
      email: 'user@example.com',
    },
  });

  if (user) {
    return user;
  }

  return await prisma.user.create({
    data: {
      email: 'user@example.com',
      password: 'password',
    },
  });
}
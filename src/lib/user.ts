import prisma from "./db";

export async function getDefaultUser() {
  const user = await prisma.user.upsert({
    where: { email: "default-user@example.com" },
    update: {},
    create: {
      email: "default-user@example.com",
      password: "password",
    },
  });
  return user;
}
'use server'

import { requireAdmin } from "@/lib/admin";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export async function restartServer() {
    await requireAdmin();

    try {
        // This command relies on the sudoers configuration being set up correctly
        // It will fail if the user 'social' cannot run this command without a password
        await execAsync('sudo systemctl restart jankbuild-web');
        return { success: true, message: 'Server restart initiated. The page will reload shortly.' };
    } catch (error: any) {
        console.error('Failed to restart server:', error);
        return {
            success: false,
            message: `Failed to restart server: ${error.message}. Ensure sudoers is configured correctly.`
        };
    }
}

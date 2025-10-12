"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function EmailSettings() {
  const [isTestingConfig, setIsTestingConfig] = useState(false);
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [configResult, setConfigResult] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testEmail, setTestEmail] = useState("");
  const [testSubject, setTestSubject] = useState("Test Email from Magic Deck Builder");
  const [testMessage, setTestMessage] = useState("<p>This is a test email. If you received this, your email configuration is working correctly!</p>");

  const testConfiguration = async () => {
    setIsTestingConfig(true);
    setConfigResult(null);
    try {
      const response = await fetch("/api/admin/test-email");
      const data = await response.json();
      setConfigResult(data.message);
    } catch (error) {
      setConfigResult("Error testing configuration");
    } finally {
      setIsTestingConfig(false);
    }
  };

  const sendTestEmail = async () => {
    if (!testEmail) {
      setTestResult("Please enter an email address");
      return;
    }

    setIsSendingTest(true);
    setTestResult(null);
    try {
      const response = await fetch("/api/admin/test-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to: testEmail,
          subject: testSubject,
          message: testMessage,
        }),
      });
      const data = await response.json();
      setTestResult(data.message || data.error);
    } catch (error) {
      setTestResult("Error sending test email");
    } finally {
      setIsSendingTest(false);
    }
  };

  return (
    <main className="container mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold">Email Settings</h1>
        <p className="text-muted-foreground mt-2">
          Configure and test email functionality
        </p>
      </div>

      <div className="space-y-6">
        {/* Email Configuration Info */}
        <Card>
          <CardHeader>
            <CardTitle>Email Configuration</CardTitle>
            <CardDescription>
              Email settings are configured in your .env file
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-muted p-4 rounded-md font-mono text-sm space-y-1">
              <div><span className="text-muted-foreground"># For Gmail (recommended):</span></div>
              <div>EMAIL_HOST=smtp.gmail.com</div>
              <div>EMAIL_PORT=587</div>
              <div>EMAIL_SECURE=false</div>
              <div>EMAIL_USER=your-email@gmail.com</div>
              <div>EMAIL_PASSWORD=your-app-password</div>
              <div>EMAIL_FROM="Magic Deck Builder &lt;your-email@gmail.com&gt;"</div>
              <div>ADMIN_EMAIL=admin@example.com</div>
              <div className="mt-3"><span className="text-muted-foreground"># For Outlook:</span></div>
              <div>EMAIL_HOST=smtp-mail.outlook.com</div>
              <div>EMAIL_PORT=587</div>
            </div>
            
            <div className="bg-yellow-500/10 border border-yellow-500/50 p-4 rounded-md">
              <p className="text-sm font-semibold mb-2">⚠️ Important for Gmail Users:</p>
              <ol className="text-sm space-y-1 list-decimal list-inside">
                <li>Go to your Google Account settings</li>
                <li>Enable 2-Step Verification</li>
                <li>Generate an "App Password" (not your regular password)</li>
                <li>Use the app password in EMAIL_PASSWORD</li>
              </ol>
            </div>

            <Button 
              onClick={testConfiguration} 
              disabled={isTestingConfig}
              variant="outline"
              className="w-full"
            >
              {isTestingConfig ? "Testing..." : "Test Email Configuration"}
            </Button>
            
            {configResult && (
              <div className={`p-3 rounded-md text-sm ${
                configResult.includes('valid') 
                  ? 'bg-green-500/10 text-green-500' 
                  : 'bg-red-500/10 text-red-500'
              }`}>
                {configResult}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Send Test Email */}
        <Card>
          <CardHeader>
            <CardTitle>Send Test Email</CardTitle>
            <CardDescription>
              Send a test email to verify your configuration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="testEmail">Recipient Email</Label>
              <Input
                id="testEmail"
                type="email"
                placeholder="test@example.com"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="testSubject">Subject</Label>
              <Input
                id="testSubject"
                type="text"
                value={testSubject}
                onChange={(e) => setTestSubject(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="testMessage">Message (HTML supported)</Label>
              <Textarea
                id="testMessage"
                rows={6}
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
              />
            </div>

            <Button 
              onClick={sendTestEmail} 
              disabled={isSendingTest}
              className="w-full"
            >
              {isSendingTest ? "Sending..." : "Send Test Email"}
            </Button>
            
            {testResult && (
              <div className={`p-3 rounded-md text-sm ${
                testResult.includes('success') 
                  ? 'bg-green-500/10 text-green-500' 
                  : 'bg-red-500/10 text-red-500'
              }`}>
                {testResult}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Email Features */}
        <Card>
          <CardHeader>
            <CardTitle>Email Features</CardTitle>
            <CardDescription>
              Emails are automatically sent for these events
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <strong>Welcome Email:</strong> Sent when new users register
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                <strong>Email Verification:</strong> (Coming soon) Verify email addresses
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                <strong>Password Reset:</strong> (Coming soon) Allow users to reset passwords
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                <strong>Admin Notifications:</strong> Notify admins of important events
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

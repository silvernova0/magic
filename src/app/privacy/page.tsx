import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PrivacyPage() {
    return (
        <div className="container mx-auto p-4 sm:p-6 lg:p-8 max-w-4xl">
            <Card>
                <CardHeader>
                    <CardTitle className="text-3xl font-bold">Privacy Policy</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6 text-muted-foreground">
                    <section>
                        <h2 className="text-xl font-semibold text-foreground mb-2">1. Information We Collect</h2>
                        <p>
                            We only collect the minimum information necessary to provide our services:
                        </p>
                        <ul className="list-disc pl-6 mt-2 space-y-1">
                            <li><strong>Email Address:</strong> Used solely for authentication, account recovery, and essential service notifications.</li>
                            <li><strong>Deck Data:</strong> We store the decks you generate and save to your account.</li>
                            <li><strong>Usage Data:</strong> We track anonymous usage statistics (such as total decks generated) to improve the service.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-foreground mb-2">2. How We Use Your Information</h2>
                        <p>
                            Your data is used exclusively for:
                        </p>
                        <ul className="list-disc pl-6 mt-2 space-y-1">
                            <li>Providing and maintaining the JankBuild service.</li>
                            <li>Managing your account and login sessions.</li>
                            <li>Improving our deck generation algorithms.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-foreground mb-2">3. Data Sharing</h2>
                        <p>
                            We <strong>do not</strong> sell, trade, or rent your personal identification information to others. We do not share your data with third parties except as required by law.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-foreground mb-2">4. Data Security</h2>
                        <p>
                            We implement appropriate data collection, storage, and processing practices and security measures to protect against unauthorized access to your personal information.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-foreground mb-2">5. Contact Us</h2>
                        <p>
                            If you have any questions about this Privacy Policy, please contact us via the feedback form in the application.
                        </p>
                    </section>

                    <div className="pt-6 text-sm">
                        <p>Last updated: November 2025</p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

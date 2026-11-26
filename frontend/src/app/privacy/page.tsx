export default function PrivacyPolicyPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-4 py-8 text-sm text-zinc-300">
      <h1 className="text-2xl font-semibold text-zinc-100">Privacy Policy — InstaPilot AI (pilot.ai)</h1>
      <p className="text-xs text-zinc-400">Effective Date: November 26, 2026</p>
      <p>
        InstaPilot AI (&ldquo;pilot.ai&rdquo;) connects to Instagram Professional accounts via official
        Meta APIs solely to process authorized Direct Messages, comments, and workspace CRM data.
      </p>
      <h2 className="text-base font-semibold text-zinc-100">Data We Process</h2>
      <ul className="list-disc pl-5 space-y-1">
        <li>Instagram account profile metadata and encrypted OAuth access tokens.</li>
        <li>Incoming messages, comments, and customer interaction records scoped to your workspace.</li>
      </ul>
      <h2 className="text-base font-semibold text-zinc-100">Data Isolation & Security</h2>
      <p>
        We never store Instagram passwords, never sell customer data, and strictly isolate data per
        workspace and Instagram account. OAuth tokens are encrypted at rest.
      </p>
      <h2 className="text-base font-semibold text-zinc-100">Contact</h2>
      <p>For privacy inquiries, contact: karthiksalupala@gmail.com</p>
    </div>
  );
}

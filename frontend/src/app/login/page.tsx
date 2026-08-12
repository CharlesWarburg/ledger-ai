import { AuthForm } from "@/components/auth/auth-form";
import { AuthLayout } from "@/components/auth/auth-layout";

export default function LoginPage() {
  return (
    <AuthLayout
      description="Use the account connected to your Ledger AI workspace."
      eyebrow="Welcome back"
      title="Sign in to continue"
    >
      <AuthForm mode="login" />
    </AuthLayout>
  );
}

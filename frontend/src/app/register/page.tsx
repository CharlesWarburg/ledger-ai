import { AuthForm } from "@/components/auth/auth-form";
import { AuthLayout } from "@/components/auth/auth-layout";

export default function RegisterPage() {
  return (
    <AuthLayout
      description="Create your workspace account. You will be signed in immediately."
      eyebrow="Get started"
      title="Create your account"
    >
      <AuthForm mode="register" />
    </AuthLayout>
  );
}

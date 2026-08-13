import type { UserResponse } from "@/lib/api";
import { LogoutButton } from "@/components/auth/logout-button";
import { PageHeading } from "@/components/ui/page-heading";

function dateTime(value: string) {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export function SettingsView({ user }: { user: UserResponse }) {
  return <div className="settings-stage">
    <PageHeading title="Settings" description="Review your account, security and session details." />
    <div className="settings-layout">
      <aside className="settings-index"><span>Account settings</span><a href="#profile" className="active">Profile</a><a href="#security">Security</a><a href="#session">Session</a></aside>
      <div className="settings-content">
        <section className="settings-card" id="profile"><div className="settings-card-heading"><div><span>01</span><h2>Account profile</h2><p>Your identity and access level in Ledger AI.</p></div><i className={user.is_active ? "active" : "inactive"}>{user.is_active ? "Active" : "Inactive"}</i></div><div className="settings-fields"><label><span>Email address</span><input readOnly value={user.email} /><small>Email changes require a backend account-update endpoint.</small></label><label><span>Account role</span><input className="capitalize" readOnly value={user.role} /></label><label className="full"><span>Account ID</span><input readOnly value={user.id} /></label></div></section>
        <section className="settings-card" id="security"><div className="settings-card-heading"><div><span>02</span><h2>Password and security</h2><p>Your account currently authenticates with an email and password.</p></div></div><div className="settings-locked-row"><span>••••••••••••</span><div><strong>Password changes are not available yet</strong><small>The backend currently provides login and identity verification, but no password-update endpoint.</small></div><i>Locked</i></div></section>
        <section className="settings-card" id="session"><div className="settings-card-heading"><div><span>03</span><h2>Account activity</h2><p>Backend timestamps associated with this account.</p></div></div><div className="settings-meta"><div><span>Account created</span><strong>{dateTime(user.created_at)}</strong></div><div><span>Last account update</span><strong>{dateTime(user.updated_at)}</strong></div></div><div className="settings-session-action"><div><strong>End this session</strong><small>You will need your email and password to sign in again.</small></div><LogoutButton /></div></section>
      </div>
    </div>
  </div>;
}

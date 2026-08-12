"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { apiRequest, ApiError } from "@/lib/api";
import type { CustomerCreate, CustomerResponse } from "@/lib/api";
import { PageHeading } from "@/components/ui/page-heading";

type PanelState = { mode: "create" } | { mode: "edit"; customer: CustomerResponse } | null;

const emptyCustomer: CustomerCreate = {
  name: "",
  email: "",
  phone: "",
  address_line_1: "",
  address_line_2: "",
  city: "",
  postal_code: "",
  country_code: "",
  vat_number: "",
};

function initials(name: string): string {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function valueOrNull(formData: FormData, key: string): string | null {
  const value = String(formData.get(key) ?? "").trim();
  return value || null;
}

function customerPayload(formData: FormData): CustomerCreate {
  return {
    name: String(formData.get("name") ?? "").trim(),
    email: valueOrNull(formData, "email"),
    phone: valueOrNull(formData, "phone"),
    address_line_1: valueOrNull(formData, "address_line_1"),
    address_line_2: valueOrNull(formData, "address_line_2"),
    city: valueOrNull(formData, "city"),
    postal_code: valueOrNull(formData, "postal_code"),
    country_code: valueOrNull(formData, "country_code")?.toUpperCase() ?? null,
    vat_number: valueOrNull(formData, "vat_number")?.toUpperCase() ?? null,
  };
}

function messageFrom(error: unknown): string {
  return error instanceof ApiError ? error.message : "Unable to complete this request. Please try again.";
}

export function CustomersView() {
  const [customers, setCustomers] = useState<CustomerResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [panel, setPanel] = useState<PanelState>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const loadCustomers = useCallback(async () => {
    try {
      setCustomers(await apiRequest<CustomerResponse[]>("/customers", { query: { limit: 100 } }));
    } catch (error) {
      setLoadError(messageFrom(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiRequest<CustomerResponse[]>("/customers", { query: { limit: 100 } })
      .then((data) => {
        if (!cancelled) setCustomers(data);
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(messageFrom(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!panel) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) setPanel(null);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [panel, saving]);

  const filteredCustomers = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return customers;
    return customers.filter((customer) =>
      [customer.name, customer.email, customer.city, customer.vat_number]
        .some((value) => value?.toLowerCase().includes(normalized)),
    );
  }, [customers, query]);

  function openPanel(nextPanel: Exclude<PanelState, null>) {
    setFormError(null);
    setConfirmDelete(false);
    setPanel(nextPanel);
  }

  function retryLoad() {
    setLoading(true);
    setLoadError(null);
    void loadCustomers();
  }

  async function submitCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    const body = customerPayload(new FormData(event.currentTarget));

    try {
      if (panel?.mode === "edit") {
        const updated = await apiRequest<CustomerResponse>(`/customers/${panel.customer.id}`, { method: "PATCH", body });
        setCustomers((current) => current.map((customer) => customer.id === updated.id ? updated : customer));
      } else {
        const created = await apiRequest<CustomerResponse>("/customers", { method: "POST", body });
        setCustomers((current) => [created, ...current]);
      }
      setPanel(null);
    } catch (error) {
      setFormError(messageFrom(error));
    } finally {
      setSaving(false);
    }
  }

  async function deleteCustomer() {
    if (panel?.mode !== "edit") return;
    setSaving(true);
    setFormError(null);
    try {
      await apiRequest<void>(`/customers/${panel.customer.id}`, { method: "DELETE" });
      setCustomers((current) => current.filter((customer) => customer.id !== panel.customer.id));
      setPanel(null);
    } catch (error) {
      setFormError(messageFrom(error));
    } finally {
      setSaving(false);
    }
  }

  const selected = panel?.mode === "edit" ? panel.customer : null;
  const formValues = selected ?? emptyCustomer;

  return (
    <>
      <PageHeading
        actions={<button className="button" onClick={() => openPanel({ mode: "create" })} type="button">Add customer</button>}
        description="Manage the people and businesses you invoice."
        title="Customers"
      />

      <section className="customer-toolbar">
        <label className="search-field">
          <span aria-hidden="true">⌕</span>
          <span className="sr-only">Search customers</span>
          <input onChange={(event) => setQuery(event.target.value)} placeholder="Search name, email, city, or VAT number" type="search" value={query} />
        </label>
        <span className="customer-count">{customers.length} {customers.length === 1 ? "customer" : "customers"}</span>
      </section>

      {loading ? (
        <div aria-label="Loading customers" className="customer-list loading-list" role="status">{Array.from({ length: 4 }).map((_, index) => <div className="customer-row skeleton-row" key={index} />)}</div>
      ) : loadError ? (
        <div className="state-card error-state"><div className="state-icon">!</div><h2>Customers couldn’t load</h2><p>{loadError}</p><button className="button" onClick={retryLoad} type="button">Try again</button></div>
      ) : customers.length === 0 ? (
        <div className="state-card"><div className="state-icon">+</div><h2>Add your first customer</h2><p>Customer details will be ready when you create invoices and track payments.</p><button className="button" onClick={() => openPanel({ mode: "create" })} type="button">Add customer</button></div>
      ) : filteredCustomers.length === 0 ? (
        <div className="state-card small-state"><div className="state-icon">⌕</div><h2>No matching customers</h2><p>Try a different name, email, city, or VAT number.</p></div>
      ) : (
        <div className="customer-list">
          <div aria-hidden="true" className="customer-list-head"><span>Customer</span><span>Contact</span><span>Location</span><span>VAT number</span><span /></div>
          {filteredCustomers.map((customer) => (
            <button className="customer-row" key={customer.id} onClick={() => openPanel({ mode: "edit", customer })} type="button">
              <span className="customer-identity"><span className="customer-avatar">{initials(customer.name)}</span><span><strong>{customer.name}</strong><small>Added {new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(customer.created_at))}</small></span></span>
              <span className="customer-contact"><strong>{customer.email ?? "No email"}</strong><small>{customer.phone ?? "No phone"}</small></span>
              <span>{[customer.city, customer.country_code].filter(Boolean).join(", ") || "—"}</span>
              <span>{customer.vat_number ?? "—"}</span>
              <span className="row-arrow">›</span>
            </button>
          ))}
        </div>
      )}

      {panel ? (
        <div className="drawer-layer" role="presentation">
          <button aria-label="Close customer panel" className="drawer-backdrop" disabled={saving} onClick={() => setPanel(null)} type="button" />
          <aside aria-labelledby="customer-panel-title" aria-modal="true" className="customer-drawer" role="dialog">
            <div className="drawer-heading">
              <div><span className="kicker">{panel.mode === "create" ? "New customer" : "Customer details"}</span><h2 id="customer-panel-title">{panel.mode === "create" ? "Add customer" : selected?.name}</h2></div>
              <button aria-label="Close" className="icon-button" disabled={saving} onClick={() => setPanel(null)} type="button">×</button>
            </div>

            <form className="customer-form" onSubmit={submitCustomer}>
              <div className="form-section"><h3>Contact</h3><div className="form-grid">
                <label className="form-control full"><span>Name *</span><input autoFocus defaultValue={formValues.name} maxLength={255} name="name" required /></label>
                <label className="form-control"><span>Email</span><input defaultValue={formValues.email ?? ""} maxLength={320} name="email" type="email" /></label>
                <label className="form-control"><span>Phone</span><input defaultValue={formValues.phone ?? ""} maxLength={32} name="phone" type="tel" /></label>
              </div></div>
              <div className="form-section"><h3>Address</h3><div className="form-grid">
                <label className="form-control full"><span>Address line 1</span><input defaultValue={formValues.address_line_1 ?? ""} maxLength={255} name="address_line_1" /></label>
                <label className="form-control full"><span>Address line 2</span><input defaultValue={formValues.address_line_2 ?? ""} maxLength={255} name="address_line_2" /></label>
                <label className="form-control"><span>City</span><input defaultValue={formValues.city ?? ""} maxLength={100} name="city" /></label>
                <label className="form-control"><span>Postcode</span><input defaultValue={formValues.postal_code ?? ""} maxLength={20} name="postal_code" /></label>
                <label className="form-control"><span>Country code</span><input defaultValue={formValues.country_code ?? ""} maxLength={2} minLength={2} name="country_code" placeholder="GB" /></label>
                <label className="form-control"><span>VAT number</span><input defaultValue={formValues.vat_number ?? ""} maxLength={32} name="vat_number" /></label>
              </div></div>

              {formError ? <p className="form-error" role="alert">{formError}</p> : null}

              {panel.mode === "edit" && confirmDelete ? <div className="delete-confirm" role="alert"><p>Delete <strong>{selected?.name}</strong>? This cannot be undone.</p><div><button className="text-button" disabled={saving} onClick={() => setConfirmDelete(false)} type="button">Cancel</button><button className="danger-button" disabled={saving} onClick={() => void deleteCustomer()} type="button">{saving ? "Deleting…" : "Delete customer"}</button></div></div> : null}

              <div className="drawer-actions">
                {panel.mode === "edit" && !confirmDelete ? <button className="text-button danger-text" disabled={saving} onClick={() => setConfirmDelete(true)} type="button">Delete</button> : <span />}
                <div><button className="button secondary" disabled={saving} onClick={() => setPanel(null)} type="button">Cancel</button><button className="button" disabled={saving} type="submit">{saving ? "Saving…" : panel.mode === "create" ? "Add customer" : "Save changes"}</button></div>
              </div>
            </form>
          </aside>
        </div>
      ) : null}
    </>
  );
}

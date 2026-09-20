import Link from "next/link";
import { NavIcon } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { InfoCallout, SectionHeader } from "@/components/ui";
import type { NavigationItem } from "@/lib/navigation";

const modules: Array<{ title: string; description: string; scope: string; tone: "neutral" | "accent" | "caution"; href: string; icon: NavigationItem["icon"] }> = [
  { title: "Message", description: "Classify pasted English SMS-style text as spam or ham.", scope: "SMS experiment", tone: "accent", href: "/message", icon: "message" },
  { title: "Email", description: "Compare a three-class prediction with observed text indicators.", scope: "Experimental", tone: "caution", href: "/email", icon: "email" },
  { title: "Screenshot", description: "Upload an image, extract text with Tesseract, review it, then choose an analysis.", scope: "OCR + review", tone: "neutral", href: "/screenshot", icon: "screenshot" },
  { title: "URL", description: "Inspect the characters and structure of a link without visiting it.", scope: "String only", tone: "accent", href: "/url", icon: "url" },
];

const workflow = [
  ["01", "Input", "You explicitly provide text, an image, or a URL string."],
  ["02", "ScamLens processing", "The configured ScamLens API runs the existing model, rules, or OCR."],
  ["03", "Observations", "Model output and directly observed indicators remain clearly separated."],
  ["04", "Limitations", "Each result explains what the evidence cannot establish."],
  ["05", "Verification", "Practical next steps help you check the request independently."],
];

const scopeFacts = [
  ["Submitted URLs", "Analyzed as strings and never visited by ScamLens."],
  ["Screenshot text", "Extracted with Tesseract OCR on the ScamLens backend and shown for review first."],
  ["Model artifacts", "Existing stored artifacts power the experimental classifiers."],
  ["Data handling", "No intentional browser persistence, account system, or analytics telemetry."],
];

export default function Overview() {
  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Inspect before you act</p>
          <h1>Analyze suspicious content with <span>evidence in view.</span></h1>
          <p className="hero-copy">Review messages, emails, screenshots, and links while keeping predictions, observations, limitations, and verification steps distinct.</p>
          <div className="hero-actions">
            <a className="button button-primary button-large" href="#workspaces">Choose an analysis <span aria-hidden="true">→</span></a>
            <a className="button button-quiet button-large" href="#workflow">See the workflow</a>
          </div>
        </div>
        <InfoCallout title="Decision support, not proof"><p>Results do not prove fraud, authenticity, maliciousness, or safety. Verify consequential requests through an independent trusted channel.</p></InfoCallout>
      </section>

      <section className="section-block" id="workspaces" aria-labelledby="workspaces-title">
        <SectionHeader eyebrow="Analysis workspaces" title="Choose the evidence you have" titleId="workspaces-title" description="Every analysis starts only after you provide content and explicitly submit it." />
        <div className="module-grid">
          {modules.map((module) => <Link className="module-card" href={module.href} key={module.href}><span className="module-top"><span className="module-icon"><NavIcon name={module.icon}/></span><StatusBadge tone={module.tone}>{module.scope}</StatusBadge></span><span className="module-body"><h3>{module.title}</h3><p>{module.description}</p></span><span className="module-action">Open workspace <span aria-hidden="true">→</span></span></Link>)}
        </div>
      </section>

      <section className="section-block" id="workflow" aria-labelledby="workflow-title">
        <SectionHeader eyebrow="How it works" title="A visible path from input to verification" titleId="workflow-title" description="The interface makes each evidence layer and decision point explicit." />
        <ol className="overview-workflow">
          {workflow.map(([number, title, description]) => <li key={number}><span>{number}</span><div><h3>{title}</h3><p>{description}</p></div></li>)}
        </ol>
      </section>

      <section className="section-block scope-section" id="scope" aria-labelledby="scope-title">
        <div>
          <SectionHeader eyebrow="Privacy & scope" title="Boundaries stated before the result" titleId="scope-title" description="ScamLens is an explicit-submission evidence workspace, not a monitoring service or a guarantee of protection." />
          <dl className="scope-facts">
            {scopeFacts.map(([term, description]) => <div key={term}><dt>{term}</dt><dd>{description}</dd></div>)}
          </dl>
        </div>
        <aside className="transparency-panel" aria-labelledby="transparency-title">
          <p className="panel-step">Transparency</p>
          <h2 id="transparency-title">Read the evaluation in context</h2>
          <p>Stored accuracy, macro-F1, and target-recall values describe separate experimental tasks. They are not a leaderboard or a general safety score.</p>
          <Link className="button button-secondary" href="/performance">View model performance <span aria-hidden="true">→</span></Link>
        </aside>
      </section>
    </>
  );
}

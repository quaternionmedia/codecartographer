import {
  SystemRenderer,
  SystemNode,
  SystemEdge,
  SystemEvent,
} from './system_renderer';

// ─── PAM architecture diagram data ───────────────────────────────────────────
// Node positions match the original frontend.html fractional layout.

const PAM_NODES: Record<string, SystemNode> = {
  app:         { label: 'Application',     sub: 'sshd',    px: .08, py: .20, type: 'service' },
  pamconf:     { label: '/etc/pam.d/',     sub: 'config',  px: .08, py: .50, type: 'core'    },
  libpam:      { label: 'libpam.so',       sub: 'runtime', px: .08, py: .80, type: 'core'    },
  mod_env:     { label: 'pam_env',         sub: 'auth',    px: .30, py: .10, type: 'auth'    },
  mod_unix_a:  { label: 'pam_unix',        sub: 'auth',    px: .30, py: .26, type: 'auth'    },
  mod_sss_a:   { label: 'pam_sss',         sub: 'auth',    px: .30, py: .42, type: 'auth'    },
  mod_ga:      { label: 'pam_google_auth', sub: 'TOTP',    px: .30, py: .58, type: 'auth'    },
  mod_deny:    { label: 'pam_deny',        sub: 'auth',    px: .30, py: .74, type: 'auth'    },
  mod_sss_ac:  { label: 'pam_sss',         sub: 'account', px: .56, py: .14, type: 'account' },
  mod_unix_ac: { label: 'pam_unix',        sub: 'account', px: .56, py: .30, type: 'account' },
  mod_nologin: { label: 'pam_nologin',     sub: 'account', px: .56, py: .46, type: 'account' },
  mod_access:  { label: 'pam_access',      sub: 'account', px: .56, py: .62, type: 'account' },
  mod_limits:  { label: 'pam_limits',      sub: 'session', px: .56, py: .78, type: 'session' },
  mod_mkhome:  { label: 'pam_mkhomedir',   sub: 'session', px: .56, py: .91, type: 'session' },
  sssd:        { label: 'SSSD',            sub: 'daemon',  px: .82, py: .24, type: 'backend' },
  sssd_nss:    { label: 'sssd_nss',        sub: 'cache',   px: .82, py: .44, type: 'backend' },
  krb:         { label: 'Kerberos KDC',    sub: 'AS-REQ',  px: .82, py: .64, type: 'backend' },
  ldap:        { label: 'LDAP/AD',         sub: 'ldap',    px: .82, py: .84, type: 'backend' },
};

const PAM_EDGES: SystemEdge[] = [
  { from: 'app',         to: 'pamconf',     style: 'dim'    },
  { from: 'app',         to: 'libpam',      style: 'dim'    },
  { from: 'libpam',      to: 'mod_env',     style: 'dashed' },
  { from: 'libpam',      to: 'mod_unix_a',  style: 'dashed' },
  { from: 'libpam',      to: 'mod_sss_a',   style: 'dashed' },
  { from: 'libpam',      to: 'mod_ga',      style: 'dashed' },
  { from: 'libpam',      to: 'mod_deny',    style: 'dashed' },
  { from: 'libpam',      to: 'mod_sss_ac',  style: 'dashed' },
  { from: 'libpam',      to: 'mod_unix_ac', style: 'dashed' },
  { from: 'libpam',      to: 'mod_nologin', style: 'dashed' },
  { from: 'libpam',      to: 'mod_access',  style: 'dashed' },
  { from: 'libpam',      to: 'mod_limits',  style: 'dashed' },
  { from: 'libpam',      to: 'mod_mkhome',  style: 'dashed' },
  { from: 'mod_sss_a',   to: 'sssd',        style: 'dim'    },
  { from: 'mod_sss_ac',  to: 'sssd',        style: 'dim'    },
  { from: 'sssd',        to: 'sssd_nss',    style: 'dim'    },
  { from: 'sssd',        to: 'krb',         style: 'dim'    },
  { from: 'sssd',        to: 'ldap',        style: 'dim'    },
  { from: 'mod_unix_a',  to: 'sssd_nss',    style: 'dim'    },
  { from: 'mod_unix_ac', to: 'sssd_nss',    style: 'dim'    },
];

// alice SSH login via SSSD/Kerberos — ported from the original frontend.html DEMO_EVENTS
const DEMO_EVENTS: SystemEvent[] = [
  { event_type: 'pam_start',     service: 'sshd', user: 'alice', rhost: '10.0.0.42', timestamp: 0   },
  { event_type: 'module_call',   module: 'pam_env.so',         phase: 'auth',    timestamp: 0.3 },
  { event_type: 'module_result', module: 'pam_env.so',         phase: 'auth',    success: true,  timestamp: 0.5 },
  { event_type: 'module_call',   module: 'pam_sss.so',         phase: 'auth',    timestamp: 0.8 },
  { event_type: 'sssd_call',                                                       timestamp: 1.1 },
  { event_type: 'krb_call',                                                        timestamp: 1.4 },
  { event_type: 'krb_result',                                   success: true,     timestamp: 1.9 },
  { event_type: 'sssd_result',                                  success: true,     timestamp: 2.2 },
  { event_type: 'module_result', module: 'pam_sss.so',         phase: 'auth',    success: true,  timestamp: 2.5 },
  { event_type: 'module_call',   module: 'pam_sss.so',         phase: 'account', timestamp: 2.8 },
  { event_type: 'module_result', module: 'pam_sss.so',         phase: 'account', success: true,  timestamp: 3.1 },
  { event_type: 'module_call',   module: 'pam_limits.so',      phase: 'session', timestamp: 3.4 },
  { event_type: 'module_result', module: 'pam_limits.so',      phase: 'session', success: true,  timestamp: 3.7 },
  { event_type: 'session_open',  service: 'sshd', user: 'alice',                  timestamp: 4.0 },
  { event_type: 'access_granted',service: 'sshd', user: 'alice',                  timestamp: 4.5 },
];

// ─── Concrete PAM renderer ────────────────────────────────────────────────────

/**
 * Linux PAM authentication flow renderer.
 *
 * Extends SystemRenderer with PAM-specific nodes, edges, demo events and
 * event-to-visual-state mapping.
 *
 * Demo sequence: alice SSH login via SSSD/Kerberos (~5 s cycle).
 * Live mode connects to /pam/ws/live and streams real /var/log/auth.log events.
 */
export class PamRenderer extends SystemRenderer {
  readonly name = 'PAM Auth Monitor';
  protected readonly wsPath = '/pam/ws/live';

  protected getNodes(): Record<string, SystemNode> { return PAM_NODES; }
  protected getEdges(): SystemEdge[]               { return PAM_EDGES;  }
  protected getDemoEvents(): SystemEvent[]          { return DEMO_EVENTS; }

  protected handleEvent(ev: SystemEvent): void {
    const CYAN   = '#00d4ff';
    const GREEN  = '#00ffb3';
    const ORANGE = '#ff6b35';

    const type    = ev.event_type;
    const module  = (ev.module  as string | undefined) ?? '';
    const phase   = (ev.phase   as string | undefined) ?? '';
    const success = ev.success  as boolean | null | undefined;

    switch (type) {
      case 'pam_start':
        this.setNodeState('app',     'active');
        this.setNodeState('pamconf', 'active');
        this.setNodeState('libpam',  'active');
        this.firePacket('app', 'libpam', CYAN);
        break;

      case 'module_call': {
        const id = pamModuleToNode(module, phase);
        if (id) {
          this.setNodeState(id, 'active');
          this.firePacket('libpam', id, CYAN);
        }
        break;
      }

      case 'module_result': {
        const id = pamModuleToNode(module, phase);
        if (id) {
          this.setNodeState(id, success ? 'success' : 'failed');
          if (success) this.firePacket(id, 'libpam', GREEN);
        }
        break;
      }

      case 'sssd_call':
        this.setNodeState('sssd', 'active');
        this.firePacket('mod_sss_a', 'sssd', CYAN);
        break;

      case 'sssd_result':
        this.setNodeState('sssd',     success ? 'success' : 'failed');
        this.setNodeState('sssd_nss', success ? 'active'  : 'failed');
        if (success) this.firePacket('sssd', 'libpam', GREEN);
        break;

      case 'krb_call':
        this.setNodeState('krb', 'active');
        this.firePacket('sssd', 'krb', CYAN);
        break;

      case 'krb_result':
        this.setNodeState('krb', success ? 'success' : 'failed');
        if (success) this.firePacket('krb', 'sssd', GREEN);
        break;

      case 'session_open':
        this.setNodeState('mod_limits', 'success');
        this.setNodeState('mod_mkhome', 'success');
        this.firePacket('libpam', 'mod_limits', ORANGE);
        break;

      case 'access_granted':
        this.setNodeState('app',    'success');
        this.setNodeState('libpam', 'success');
        this.firePacket('libpam', 'app', GREEN);
        this.log('ACCESS GRANTED', 'ok');
        break;

      case 'access_denied':
        this.setNodeState('libpam', 'failed');
        this.setNodeState('app',    'failed');
        this.log('ACCESS DENIED', 'err');
        break;

      case 'pam_end':
        // Brief pause then reset — let the animation breathe
        setTimeout(() => this.resetAllNodes(), 2000);
        break;
    }
  }
}

// ─── PAM-private helper ───────────────────────────────────────────────────────

/**
 * Resolve a PAM module filename + phase to a node ID in PAM_NODES.
 * pam_sss.so is used for both auth and account phases (different nodes).
 * pam_unix.so is similarly phase-ambiguous.
 */
function pamModuleToNode(module: string, phase: string): string | null {
  const m = module.toLowerCase();
  if (m.includes('pam_sss'))                            return phase === 'account' ? 'mod_sss_ac'  : 'mod_sss_a';
  if (m.includes('pam_unix'))                           return phase === 'account' ? 'mod_unix_ac' : 'mod_unix_a';
  if (m.includes('pam_env'))                            return 'mod_env';
  if (m.includes('pam_limits'))                         return 'mod_limits';
  if (m.includes('pam_mkhomedir'))                      return 'mod_mkhome';
  if (m.includes('pam_google') || m.includes('pam_ga')) return 'mod_ga';
  if (m.includes('pam_nologin'))                        return 'mod_nologin';
  if (m.includes('pam_access'))                         return 'mod_access';
  if (m.includes('pam_deny'))                           return 'mod_deny';
  return null;
}

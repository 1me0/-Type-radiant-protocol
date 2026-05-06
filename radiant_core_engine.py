"""
radiant_core_engine.py — Radiant Core Engine v4.0 (compact)
License: MIT (code) / RPML v1.0 (math) / RPL v1.0 (commercial)
"""
import torch, torch.nn as nn, torch.nn.utils as utils, numpy as np, matplotlib.pyplot as plt
from typing import Dict, Optional, Tuple, Callable, List

# ========== 1. Energy Model ==========
class ConstraintFunction(nn.Module):
    def __init__(self, sd, cd, hd=128):
        super().__init__()
        self.net = nn.Sequential(utils.spectral_norm(nn.Linear(sd+cd, hd)), nn.ReLU(), utils.spectral_norm(nn.Linear(hd, sd)))
    def forward(self, P, C): return self.net(torch.cat([P, C], dim=-1))

class EnergyModel(nn.Module):
    def __init__(self, sd, cd, hd=128):
        super().__init__()
        self.constraint = ConstraintFunction(sd, cd, hd)
        self.residual = nn.Sequential(utils.spectral_norm(nn.Linear(sd+cd, hd)), nn.ReLU(), utils.spectral_norm(nn.Linear(hd, 1)))
        self.real: Optional[Callable[[torch.Tensor, torch.Tensor], torch.Tensor]] = None
    def register_real(self, fn): self.real = fn
    def forward(self, P, C):
        phi_l = self.constraint(P, C)
        E_l = (phi_l**2).sum(-1, keepdim=True)
        E_r = (self.real(P, C)**2).sum(-1, keepdim=True) if self.real else 0.0
        return torch.tanh(E_l + E_r + self.residual(torch.cat([P, C], dim=-1)))

# ========== 2. Dynamics field μF ==========
class ArchPot(nn.Module):
    def __init__(self, sd, hd=128): super().__init__(); self.net = nn.Sequential(utils.spectral_norm(nn.Linear(sd, hd)), nn.Tanh(), utils.spectral_norm(nn.Linear(hd, 1)))
    def forward(self, P): return self.net(P)

class MuF(nn.Module):
    def __init__(self, sd, hd=128): super().__init__(); self.pot = ArchPot(sd, hd)
    def forward(self, P, create_graph=False):
        P_r = P.clone().detach().requires_grad_(True)
        Phi = self.pot(P_r).sum()
        return -0.5*torch.tanh(torch.autograd.grad(Phi, P_r, create_graph=create_graph)[0])

# ========== 3. Uncertainty ==========
class UncertaintyNet(nn.Module):
    def __init__(self, cd, sigma0=0.01, learn_gamma=False, gamma_init=0.5):
        super().__init__(); self.s0=sigma0
        if learn_gamma: self.gamma = nn.Parameter(torch.tensor(gamma_init))
        else: self.register_buffer('gamma', torch.tensor(gamma_init))
        self.mod = nn.Sequential(nn.Linear(cd,16), nn.Tanh(), nn.Linear(16,1))
    def forward(self, gn, C):
        g = self.gamma.to(gn.device) if isinstance(self.gamma, torch.Tensor) else torch.tensor(self.gamma, device=gn.device)
        return self.s0 + g*gn*(1.0+torch.tanh(self.mod(C)))

# ========== 4. Helpers ==========
def energy_grad(em, P, C, create_graph=False):
    P_r = P.clone().detach().requires_grad_(True); E = em(P_r, C)
    return E, torch.autograd.grad(E.sum(), P_r, create_graph=create_graph)[0]

def adapt_dt(bdt, s, gn, mx=1.0, mn=0.01): return torch.clamp(bdt/(1.0+s+gn), mn, mx)

# ========== 5. System ==========
class System(nn.Module):
    def __init__(self, sd, cd, learn_gamma=False): super().__init__(); self.energy=EnergyModel(sd, cd); self.muF=MuF(sd); self.unc=UncertaintyNet(cd, learn_gamma=learn_gamma)
    def step(self, P, C, alpha=0.05, beta=0.02, bdt=1.0, ns=0.1, mode='sde', create_graph=False):
        E, gE = energy_grad(self.energy, P, C, create_graph); gn = gE.norm(dim=-1, keepdim=True)
        sigma = self.unc(gn, C); dt = adapt_dt(bdt, sigma, gn)
        drift = self.muF(P, create_graph); noise = torch.randn_like(P)*(sigma*ns*dt.sqrt())
        if mode=='sde': Pn = P - alpha*gE*dt + beta*drift*dt + noise
        elif mode=='projection': Pi = P - alpha*gE; Pn = (1+beta)*Pi - beta*P + noise
        else: raise ValueError
        return Pn, E.detach(), sigma.detach(), dt.detach()

# ========== 6. Presence ==========
def stab(E, s): return torch.sigmoid(-(E+s))
def resp(P, Pn): n = torch.norm(Pn-P, dim=-1, keepdim=True); return torch.exp(-((n-0.5)**2)/0.1)
def rel(Pn, targ): cos=nn.CosineSimilarity(dim=-1)(Pn, targ); return (cos+1.0)/2.0
def comp_pres(E, s, P, Pn, targ=None, w=(0.4,0.3,0.3)):
    return w[0]*stab(E,s) + w[1]*resp(P,Pn) + w[2]*rel(Pn,targ) if targ is not None else w[0]*stab(E,s)+w[1]*resp(P,Pn)+w[2]*torch.ones_like(E)
def pres_simple(E,s): return stab(E,s)

# ========== 7. Core Engine ==========
class RadiantCoreEngine(nn.Module):
    def __init__(self, sd, cd): super().__init__(); self.sys=System(sd,cd); self.register_buffer('alpha',torch.tensor(0.05)); self.register_buffer('beta',torch.tensor(0.02)); self.adapt_en=False; self.pth=0.3; self.amin=0.01; self.bmax=0.1; self.ad=0.95; self.bb=1.2
    def enable_adaptation(self): self.adapt_en=True
    def disable_adaptation(self): self.adapt_en=False
    def _adjust(self, pres): 
        if self.adapt_en and pres.mean().item()<self.pth:
            self.alpha.data=torch.max(self.alpha*self.ad, torch.tensor(self.amin, device=self.alpha.device))
            self.beta.data=torch.min(self.beta*self.bb, torch.tensor(self.bmax, device=self.beta.device))
    def rollout(self, P, C, steps=1, mode='sde', training=False, target=None, **kw):
        for _ in range(steps):
            if not training: P=P.detach()
            Pn,E,s,dt=self.sys.step(P,C,self.alpha.item(),self.beta.item(),mode=mode,create_graph=training,**kw)
            pres=comp_pres(E,s,P,Pn,target) if target is not None else pres_simple(E,s)
            if training: self._adjust(pres)
            P=Pn
        return {'state':P,'energy':E,'uncertainty':s,'dt':dt,'presence':pres}
    def rollout_traj(self, P, C, steps=1, mode='sde', training=False, target=None, **kw):
        traj=[]; 
        for _ in range(steps):
            if not training: P=P.detach()
            Pn,E,s,dt=self.sys.step(P,C,self.alpha.item(),self.beta.item(),mode=mode,create_graph=training,**kw)
            pres=comp_pres(E,s,P,Pn,target) if target is not None else pres_simple(E,s)
            if training: self._adjust(pres)
            traj.append({'state':Pn,'energy':E,'uncertainty':s,'dt':dt,'presence':pres}); P=Pn
        return traj
    def forward(self, P, C, **kw): return self.rollout(P,C,**kw)

# ========== 8. Training ==========
def train_engine(engine, data, real_pres_fn=None, ext_eval=None, epochs=50, lr=1e-3, bs=32, device='cpu',
                 lpres=0.1, ltask=1.0, rollout_steps=1, bptt_int=3):
    engine.train().to(device); opt=torch.optim.Adam(engine.parameters(), lr=lr)
    sch=torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs); loss_fn=nn.MSELoss()
    for ep in range(epochs):
        tl=0.0; idx=torch.randperm(len(data))
        for i in range(0,len(data),bs):
            b=idx[i:i+bs]; P=torch.stack([data[j][0] for j in b]).to(device); C=torch.stack([data[j][1] for j in b]).to(device)
            T=torch.stack([data[j][2] for j in b]).to(device); opt.zero_grad()
            if rollout_steps==1:
                out=engine.rollout(P,C,steps=1,training=True,target=T)
                P_pred=out['state']; task_l=loss_fn(P_pred,T)
                pres_l = loss_fn(out['presence'].squeeze(-1), real_pres_fn(P_pred,C).squeeze(-1)) if real_pres_fn else torch.zeros(1,device=device)
                ext_l = torch.tensor(1.0-ext_eval(P_pred,T),device=device) if ext_eval else torch.zeros(1,device=device)
                loss=ltask*task_l+lpres*pres_l+0.1*ext_l; loss.backward()
            else:
                loss=0.0; P_b=P.clone(); C_b=C.clone()
                for s in range(rollout_steps):
                    out=engine.rollout(P_b,C_b,steps=1,training=True,target=T)
                    P_pred=out['state']; step_t=loss_fn(P_pred,T)
                    step_p=loss_fn(out['presence'].squeeze(-1), real_pres_fn(P_pred,C_b).squeeze(-1)) if real_pres_fn else torch.zeros(1,device=device)
                    step_e=torch.tensor(1.0-ext_eval(P_pred,T),device=device) if ext_eval else torch.zeros(1,device=device)
                    step_l=ltask*step_t+lpres*step_p+0.1*step_e; step_l.backward(); loss+=step_l.item()
                    P_b = P_pred.detach() if (s+1)%bptt_int==0 else P_pred
                loss/=rollout_steps
            utils.clip_grad_norm_(engine.parameters(),1.0); opt.step(); tl+=loss if rollout_steps==1 else loss/rollout_steps
        sch.step()
        if ep%10==0: print(f"Epoch {ep}: loss {tl/len(data):.4f}")
    return engine

# ========== 9. Data ==========
def gen_osc(n=200, dim=4, damp=0.1, noise=0.05):
    d=[]; 
    for _ in range(n): x=torch.randn(dim)*2; ctx=torch.sin(torch.linspace(0,2*np.pi,dim)); targ=(1-damp)*x+noise*torch.randn(dim); d.append((x,ctx,targ))
    return d

def osc_pres(P,C): return torch.exp(-torch.norm(P,dim=-1,keepdim=True))

# ========== 10. Main ==========
if __name__=='__main__':
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    sd,cd=4,4; eng=RadiantCoreEngine(sd,cd).to(dev)
    def cstr(P,C): return torch.relu(torch.norm(P,dim=-1,keepdim=True)-10.0)
    eng.sys.energy.register_real(cstr)
    data=gen_osc(300,sd)
    eng=train_engine(eng,data,real_pres_fn=osc_pres,epochs=10,lr=1e-3,bs=32,device=dev,lpres=0.2,rollout_steps=1)
    eng=train_engine(eng,data,real_pres_fn=osc_pres,epochs=10,lr=3e-4,bs=32,device=dev,lpres=0.5,rollout_steps=5,bptt_int=2)
    P0=torch.randn(1,sd).to(dev)*2; C0=torch.sin(torch.linspace(0,2*np.pi,sd)).unsqueeze(0).to(dev)
    traj=eng.rollout_traj(P0,C0,steps=20,training=False)
    steps=np.arange(len(traj)); en=[float(t['energy'].item()) for t in traj]; pr=[float(t['presence'].item()) for t in traj]; un=[float(t['uncertainty'].item()) for t in traj]
    plt.figure(figsize=(10,6))
    plt.subplot(3,1,1); plt.plot(steps,en,'b-'); plt.ylabel('Energy')
    plt.subplot(3,1,2); plt.plot(steps,pr,'g-'); plt.ylabel('Presence')
    plt.subplot(3,1,3); plt.plot(steps,un,'r-'); plt.ylabel('Uncertainty'); plt.xlabel('Step')
    plt.tight_layout(); plt.show()
    print(f"Final energy: {en[-1]:.4f}, presence: {pr[-1]:.4f}")

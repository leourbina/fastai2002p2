# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/clean/14_augment.ipynb.

# %% auto 0
__all__ = ['summary', 'show_image_batch', 'CapturePreds', 'capture_preds', 'rand_erase', 'RandErase']

# %% ../nbs/clean/14_augment.ipynb 2
import torch
import random
import fastcore.all as fc

from torch import nn
from torch.nn import init

from .datasets import *
from .conv import *
from .learner import *
from .activations import * 
from .init import *
from .sgd import *
from .resnet import *

# %% ../nbs/clean/14_augment.ipynb 13
def _flops(x, h, w):
    if x.dim() <= 3: return x.numel()
    if x.dim() == 4: return x.numel()*h*w

@fc.patch
def summary(self:Learner, isleaf=fc.risinstance(ResBlock)):
    res = '|Module|Input|Output|Num params|MFlops|\n|--|--|--|--|--|\n'
    totp, totf = 0, 0
    @hook
    def _f(hook, model, inp, out):
        nonlocal res, totp, totf
        num_params = sum(o.numel() for o in model.parameters())
        totp += num_params
        *_, h, w = out.shape
        flops = sum(_flops(o, h, w) for o in model.parameters())/1e6
        totf += flops
        res += f'|{type(model).__name__}|{tuple(inp[0].shape)}|{tuple(out.shape)}|{num_params}|{flops:.1f}|\n'
    
    with Hooks(*model_iter(self.model, isleaf=isleaf), h=_f) as h: self.fit(1, lr=0, cbs=SingleBatchCB())
    print(f"Total params: {totp} - Mflops: {totf:.1f}")
    
    if fc.IN_NOTEBOOK:
        from IPython.display import Markdown
        return Markdown(res)
    else: print(res)        

# %% ../nbs/clean/14_augment.ipynb 35
@fc.patch
@fc.delegates(show_images)
def show_image_batch(self: Learner, max_n=9, cbs=None, **kwargs):
    self.fit(1, cbs=[SingleBatchCB()] + fc.L(cbs))
    show_images(self.batch[0][:max_n], **kwargs)

# %% ../nbs/clean/14_augment.ipynb 48
class CapturePreds(Callback):
    def before_fit(self, learn): self.all_inputs, self.all_preds, self.all_targs = [], [], []
    def after_batch(self, learn: Learner): 
        self.all_inputs.append(to_cpu(learn.batch[0]))
        self.all_preds.append(to_cpu(learn.preds))
        self.all_targs.append(to_cpu(learn.batch[1]))
    def after_fit(self, learn: Learner):
        self.all_preds, self.all_targs, self.all_inputs = map(torch.cat, [self.all_preds, self.all_targs, self.all_inputs])

# %% ../nbs/clean/14_augment.ipynb 49
@fc.patch
def capture_preds(self: Learner, cbs=None, inputs=False):
    cp = CapturePreds()
    self.fit(1, train=False, cbs=[cp] + fc.L(cbs))
    res = cp.all_preds, cp.all_targs
    if inputs: res = res + (cp.all_inputs,)
    return res

# %% ../nbs/clean/14_augment.ipynb 69
def _rand_erase1(x, pct, xm, xs, mn, mx):
    szx = int(xbt.shape[-2]*pct)
    szy = int(xbt.shape[-1]*pct)
    stx = int(random.random()*(1-pct)*xbt.shape[-2])
    sty = int(random.random()*(1-pct)*xbt.shape[-1])
    init.normal_(x[:,:, stx:stx+szx, sty:sty+szy], mean=xm, std=xs)
    x.clamp_(mn, mx)

# %% ../nbs/clean/14_augment.ipynb 73
def rand_erase(x, pct=0.2, max_num=5):
    xm, xs, mn, mx = x.mean(), x.std(), x.min(), x.max()
    num = random.randint(0, max_num)
    for i in range(num): _rand_erase1(x, pct, xm, xs, mn, mx)
    return x
    
class RandErase(nn.Module):
    def __init__(self, pct=0.2, max_num=5):
        super().__init__()
        self.pct, self.max_num = pct, max_num
    
    def forward(self, x): return rand_erase(x, self.pct, self.max_num)

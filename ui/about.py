from __future__ import annotations

import streamlit as st

from ui.brand import intelligence_label, brand_mark


def render_about() -> None:
    # This page intentionally owns its layout CSS. The founder story should read as
    # a warm editorial letter inside CampaignLab's darker product shell, with the
    # support rail visible beside it on desktop and stacked beneath it on mobile.
    st.html(
        r'''
        <style>
        .cl-about-intro{max-width:980px;margin:.15rem 0 1.55rem}
        .cl-about-intro h1{margin:.1rem 0 .45rem;font-size:clamp(2.15rem,4vw,3.4rem);line-height:1.03}
        .cl-about-intro p{margin:0;max-width:860px;color:#d8dcda;font-size:1.08rem;line-height:1.6;font-weight:620}

        .cl-founder-paper{
          position:relative;
          overflow:hidden;
          border:1px solid rgba(255,247,226,.52);
          border-radius:24px;
          padding:2.5rem 2.55rem 2.3rem;
          background:
            radial-gradient(circle at 15% 0%,rgba(255,255,255,.48),transparent 28%),
            radial-gradient(circle at 100% 100%,rgba(189,164,120,.12),transparent 34%),
            linear-gradient(145deg,#f5efe4 0%,#eee5d7 52%,#e9dfcf 100%) !important;
          color:#202526 !important;
          box-shadow:0 32px 90px rgba(0,0,0,.38),0 1px 0 rgba(255,255,255,.75) inset;
        }
        .cl-founder-paper:before{
          content:"";position:absolute;inset:0;pointer-events:none;opacity:.3;
          background-image:linear-gradient(rgba(40,45,45,.035) 1px,transparent 1px);
          background-size:100% 31px;
        }
        .cl-founder-paper>*{position:relative;z-index:1}
        .cl-paper-head{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding-bottom:1rem;margin-bottom:1.45rem;border-bottom:1px solid rgba(32,37,38,.16)}
        .cl-paper-label{display:flex;align-items:center;gap:.45rem;font-size:.68rem;font-weight:900;letter-spacing:.14em;text-transform:uppercase;color:#666e6c}
        .cl-paper-name{font-size:.78rem;font-weight:850;color:#505856}
        .cl-founder-paper p{max-width:720px;color:#303637 !important;font-size:1.02rem;line-height:1.78;margin:1rem 0}
        .cl-founder-paper .lead{font-size:1.08rem;line-height:1.7;font-weight:700;color:#202526 !important;margin:.1rem 0 1rem}
        .cl-founder-paper .pull{max-width:720px;margin:1.65rem 0;padding:.15rem 0 .15rem 1rem;border-left:2px solid rgba(110,131,31,.55);font-size:1.18rem;line-height:1.5;font-weight:800;letter-spacing:-.012em;color:#202526}
        .cl-founder-paper .beat{max-width:720px;font-size:1.02rem;font-weight:800;color:#202526;margin:1rem 0}
        .cl-founder-paper .call{max-width:720px;margin:1.55rem 0;padding:.1rem 0 .1rem 1rem;border-left:2px solid rgba(110,131,31,.55);font-size:1.15rem;line-height:1.5;font-weight:800;color:#202526}
        .cl-founder-paper .finale{max-width:720px;margin:2.15rem 0 0;padding:1.4rem 0 0;border-top:1px solid rgba(32,37,38,.16)}
        .cl-founder-paper .finale small{display:block;font-size:.65rem;font-weight:900;letter-spacing:.13em;color:#707876}
        .cl-founder-paper .finale strong{display:block;font-size:2.65rem;line-height:1;color:#6e831f;margin:.4rem 0 .9rem;letter-spacing:-.04em}
        .cl-founder-paper .finale p{font-size:1.15rem;line-height:1.52;font-weight:700;color:#202526 !important;margin:.2rem 0}
        .cl-founder-paper .signature{max-width:720px;margin-top:1.7rem;padding-top:1rem;border-top:1px solid rgba(32,37,38,.13);font-size:1.03rem;font-weight:900;color:#242a2a}
        .cl-founder-paper .signature span{display:block;margin-top:.12rem;color:#6e7572;font-size:.76rem;font-weight:750;letter-spacing:.05em}

        .cl-about-rail{position:sticky;top:1.2rem}
        .cl-about-support-v3{border:1px solid rgba(183,243,74,.30);border-radius:22px;padding:1.2rem 1.15rem;background:radial-gradient(circle at 90% 0%,rgba(183,243,74,.16),transparent 38%),linear-gradient(145deg,rgba(183,243,74,.08),rgba(255,255,255,.025));box-shadow:0 22px 60px rgba(0,0,0,.24)}
        .cl-about-support-v3 .kicker,.cl-about-rule-v3 .kicker{font-size:.64rem;font-weight:900;letter-spacing:.13em;color:#dfff9e;margin-bottom:.5rem}
        .cl-about-support-v3 h3{margin:.1rem 0 .45rem;font-size:1.3rem;line-height:1.18}
        .cl-about-support-v3 p{margin:0 0 .9rem;color:#bdc5c2;font-size:.84rem;line-height:1.55}
        .cl-about-support-v3 .button{display:flex;align-items:center;justify-content:space-between;gap:.7rem;border:1px solid rgba(183,243,74,.38);border-radius:12px;padding:.72rem .8rem;font-size:.82rem;font-weight:850;color:#efffcb;background:rgba(183,243,74,.045)}
        .cl-about-support-v3 .button span{font-size:.62rem;letter-spacing:.08em;color:#aeb7ae}
        .cl-about-rule-v3{margin-top:.85rem;border:1px solid var(--cl-border);border-radius:18px;padding:1rem;background:rgba(255,255,255,.02)}
        .cl-about-rule-v3 .kicker{color:#ff9a83}
        .cl-about-rule-v3 b{display:block;font-size:1.02rem}
        .cl-about-rule-v3 p{margin:.3rem 0 0;color:var(--cl-muted);font-size:.8rem;line-height:1.5}

        .cl-about-principles-v3{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin:1.35rem 0 .7rem}
        .cl-about-principles-v3>div{border-top:1px solid var(--cl-border);padding:.78rem .15rem 0}
        .cl-about-principles-v3 span{display:block;color:#b7f34a;font-size:.64rem;font-weight:900;letter-spacing:.1em;margin-bottom:.25rem}
        .cl-about-principles-v3 b{font-size:.8rem;line-height:1.35}

        @media(max-width:900px){
          .cl-founder-paper{padding:1.75rem 1.5rem 1.6rem}
          .cl-about-rail{position:static}
          .cl-about-principles-v3{grid-template-columns:1fr 1fr}
        }
        @media(max-width:600px){
          .cl-founder-paper{padding:1.45rem 1.15rem 1.35rem;border-radius:19px}
          .cl-paper-head{align-items:flex-start;flex-direction:column;gap:.3rem}
          .cl-founder-paper .pull{font-size:1.2rem}
          .cl-founder-paper .finale strong{font-size:2.25rem}
          .cl-about-principles-v3{grid-template-columns:1fr}
        }
        </style>
        '''
    )

    intelligence_label("Behind the Lab")
    st.html(
        '''<section class="cl-about-intro">
        <h1>I like difficult questions.</h1>
        <p>The ones where the first answer sounds convincing, the data complicates it, people disagree — and somebody still has to decide.</p>
        </section>'''
    )

    letter_col, side_col = st.columns([2.15, 0.85], gap="large")

    with letter_col:
        st.html(
            f'''<article class="cl-founder-paper" style="background:linear-gradient(145deg,#f5efe4 0%,#eee5d7 52%,#e9dfcf 100%);color:#202526;">
              <div class="cl-paper-head">
                <div class="cl-paper-label">{brand_mark("xs")} &nbsp; BEHIND CAMPAIGNLAB</div>
                <div class="cl-paper-name">Hassan Abrar</div>
              </div>

              <p class="lead">Maybe because life has given me a few.</p>

              <p>CampaignLab wasn't born from some grand founder vision scribbled on a whiteboard. It started during a period when there were more question marks in my life than I particularly enjoyed.</p>

              <p>Some things were moving slower than I wanted. Some doors were outside my control. And I got tired of feeling like what I could do was something I had to keep explaining to people.</p>

              <p><b>So I decided to build.</b></p>

              <p>The original idea was smaller: bring together what I'd learned across marketing, analytics, experimentation and data science, add AI to the mix, and see what I could make.</p>

              <p>Part of it was practical. <b>Part of it was probably me saying: fine. I'll show you.</b></p>

              <p>Then it got a little out of hand.</p>

              <p>I built a strategy generator. Then immediately became suspicious of the strategy generator.</p>

              <p>So I made it challenge itself.</p>

              <p>Then I wanted numbers behind the arguments. Then real data. Experiments. Causal inference. An analytics engine. Eventually, I wanted it to look at a messy dataset and understand what the hell it was looking at.</p>

              <p>Somewhere along the way, the question changed from:</p>

              <div class="call">Can I build this?<br><br>How far can I take it?</div>

              <p>And somewhere in there, I figured out what I actually wanted CampaignLab to do.</p>

              <p><b>I wanted it to ask the annoying questions so you don't have to.</b></p>

              <p>Challenge the strategy. Check the evidence. Run the numbers. Find the assumption hiding underneath the confident answer. Ask what would have to be true. Ask what could make it wrong.</p>

              <p>And then, importantly:</p>

              <p><b>stop asking questions and make the call.</b></p>

              <p>Because good analysis shouldn't leave you standing at the same crossroads with a more sophisticated list of reasons to be confused.</p>

              <p><b>It should converge.</b></p>

              <p>Here's what I'd do. Here's why. Here's how confident I'd be. Here's what could change my mind.</p>

              <p>That's the closed loop I've been trying to build.</p>

              <p>AI makes it possible to ask an extraordinary number of questions now. I don't think the goal is to make people answer all of them.</p>

              <div class="pull">The system should do the worrying.<br>You should get the clarity.</div>

              <p>Maybe there's something fitting about building that during a period of uncertainty.</p>

              <p>I couldn't control every decision being made around me.</p>

              <p><b>But I could control what I became capable of.</b></p>

              <p>So I kept building.</p>
              <p>I still am.</p>

              <div class="finale">
                <small>SOMETIMES REALITY DISAGREES</small>
                <strong>Good.</strong>
                <p>I'm strong enough to face it.<br><b>So my ideas better be as well.</b></p>
              </div>

              <div class="signature">Hassan Abrar<span>CampaignLab</span></div>
            </article>'''
        )

    with side_col:
        st.html(
            '''<aside class="cl-about-rail">
              <div class="cl-about-support-v3">
                <div class="kicker">SUPPORT THE LAB</div>
                <h3>Keep the experiment moving.</h3>
                <p>CampaignLab is being built in public, one uncomfortable question at a time. A way to support the work is coming later.</p>
                <div class="button">♡ Support CampaignLab <span>COMING SOON</span></div>
              </div>
              <div class="cl-about-rule-v3">
                <div class="kicker">THE LAB RULE</div>
                <b>Reality gets the final vote.</b>
                <p>Strong ideas should survive contact with evidence.</p>
              </div>
            </aside>'''
        )

    st.html(
        '''<div class="cl-about-principles-v3">
          <div><span>01</span><b>Calculate what can be calculated.</b></div>
          <div><span>02</span><b>Challenge what is assumed.</b></div>
          <div><span>03</span><b>Test what remains uncertain.</b></div>
          <div><span>04</span><b>Make the call.</b></div>
        </div>'''
    )
    st.caption("Built with curiosity, evidence, and an unreasonable number of questions. 🧪")

/* Local companion controls. Saved values are rendered as text, never HTML. */
let rhythmLoaded = false;
const presets = {everyday:'Everyday', straight_talk:'Straight Talk', playful:'Playful', quiet:'Quiet', unfiltered:'Unfiltered'};
function safeForm(form, handler) {
  form.onsubmit = async (event) => {
    event.preventDefault();
    const submit = form.querySelector('button');
    submit.disabled = true;
    try { await handler(event); await refresh(); }
    catch (error) { toast(error.message); }
    finally { submit.disabled = false; }
  };
}
for (const [preset,label] of Object.entries(presets)) {
  const choice = button(label, async () => {
    await api('/api/personality/preset', {preset, adult_confirmed: $('#adult-unfiltered').checked});
    profileLoaded = false;
    await refresh();
    toast(label + ' is saved. The conversation stays with you.');
  }, 'preset');
  choice.dataset.preset = preset;
  $('#personality-presets').append(choice);
}
$('#voice-preview').onclick = async () => {
  try { await api('/api/speak', {text: "Hey, I'm Luma. Tell me what's on your mind. We can talk it through, or take care of something together."}); }
  catch(error) { toast(error.message); }
};
$('#interrupt').onclick = async () => {
  try { await api('/api/interrupt', {}); toast('Stopped. Your completed steps are kept.'); $('#message').focus(); }
  catch(error) { toast(error.message); }
};
$('#read-briefing').onclick = async () => {
  try { result(await api('/api/briefing', {})); }
  catch(error) { toast(error.message); }
};
$('#barge-in').onchange = e => setting('barge_in', e.target.checked);
$('#briefing-enabled').onchange = e => setting('daily_briefing_enabled', e.target.checked);
safeForm($('#quiet-form'), async () => {
  await api('/api/quiet-hours', {start:Number($('#quiet-start').value),end:Number($('#quiet-end').value)});
  await api('/api/setting',{key:'daily_briefing_hour',value:Number($('#briefing-hour').value)});
  toast('Daily rhythm saved.');
});
safeForm($('#timer-form'), async e => {
  result(await api('/api/timers/start',{name:$('#timer-name').value,seconds:Math.round(Number($('#timer-minutes').value)*60)}));
  e.target.reset();
});
safeForm($('#recipe-form'), async e => {
  const data = {title:$('#recipe-title').value,steps:$('#recipe-steps').value.split('\n').map(s=>s.trim()).filter(Boolean),source_url:$('#recipe-source').value};
  if ($('#recipe-id').value) data.id = $('#recipe-id').value;
  await api('/api/recipes/save',data); e.target.reset(); toast('Recipe saved.');
});
safeForm($('#household-form'), async e => {
  const data = {category:$('#household-category').value,title:$('#household-title').value,details:$('#household-details').value,source_url:$('#household-source').value,due_date:$('#household-date').value};
  if ($('#household-id').value) data.id = $('#household-id').value;
  await api('/api/household/save',data); e.target.reset(); toast('Household note saved.');
});
safeForm($('#memory-edit'), async e => {
  await api('/api/memory/save',{id:$('#memory-edit-id').value,text:$('#memory-edit-text').value});
  e.target.hidden = true; toast('Memory corrected.');
});
safeForm($('#agent-form'), async () => {
  const id = $('#agent-resume-id').value;
  $('#agent-submit').textContent = 'Working locally…';
  try {
    result(await api(id ? '/api/workflows/resume' : '/api/workflows/start',{goal:$('#agent-goal').value,...(id ? {id} : {})}));
    $('#agent-resume-id').value = '';
  } finally { $('#agent-submit').textContent = 'Start agent task ↗'; }
});
function groceryValues() {
  return {title:$('#grocery-title').value,items:Array.from($('#grocery-items').children).map(row=>({name:row.querySelector('input').value,quantity:Number(row.querySelector('input[type=number]').value),unit:row.querySelector('select').value}))};
}
$('#grocery-save').onclick = async () => {
  $('#grocery-save').disabled=true;
  try { const data = await api('/api/groceries/save',{...groceryValues(),...($('#grocery-local-id').value?{id:$('#grocery-local-id').value}:{})}); $('#grocery-local-id').value=data.list.id; toast(data.summary); await refresh(); }
  catch(error) { toast(error.message); }
  finally { $('#grocery-save').disabled=false; }
};
$('#household-search').oninput = () => renderHousehold(state.household.records);
function renderHousehold(records) {
  const target = $('#household-list'), query = $('#household-search').value.toLowerCase();
  empty(target,'Save a detail you want Luma to remember.');
  const matches = records.filter(r=>(r.title+' '+r.details+' '+r.category).toLowerCase().includes(query));
  if (matches.length) target.replaceChildren();
  for (const note of matches) {
    const card = make('article',undefined,'note-row');
    card.append(make('span',note.category,'eyebrow'),make('h3',note.title),make('p',note.details));
    if (note.due_date) card.append(make('p','Follow up · '+note.due_date,'footnote'));
    if (note.source_url?.startsWith('https://')) {
      const link = make('a','Open source ↗','text-button'); link.href=note.source_url; link.target='_blank'; link.rel='noreferrer'; card.append(link);
    }
    card.append(button('Edit',async()=>{
      for (const [id,key] of [['id','id'],['category','category'],['title','title'],['details','details'],['source','source_url'],['date','due_date']]) $('#household-'+id).value=note[key]||'';
      $('#household-title').focus();
    }),button('Remove',async()=>{await api('/api/household/delete',{id:note.id});await refresh();}));
    target.append(card);
  }
}
function renderCompanion(data) {
  const s = data.status, adult = s.mode!=='kids', phone = data.viewer==='phone';
  $('#agent-runs').hidden = !adult;
  $('#household').hidden = !adult;
  $('#daily-settings').hidden = phone || !adult;
  $('#recipe-form').hidden = !adult;
  $('#briefing-copy').textContent = data.household.briefing?.text || 'No saved commitments to bring forward yet.';
  if (!rhythmLoaded) {
    $('#quiet-start').value = s.quiet_hours[0]; $('#quiet-end').value = s.quiet_hours[1];
    $('#briefing-hour').value = s.daily_briefing_hour; rhythmLoaded = true;
  }
  $('#briefing-enabled').checked = s.daily_briefing_enabled;
  $('#barge-in').checked = s.barge_in;
  for (const b of document.querySelectorAll('[data-preset]')) b.setAttribute('aria-pressed',String(b.dataset.preset === (s.profile.preset || 'everyday')));
  if (s.physical_privacy?.blocked) $('#device-status').textContent = 'Physical privacy is on · capture blocked.';
  const timers = $('#timer-list'); empty(timers,'Start a timer. Call it pasta, tea, or whatever is on the stove.');
  if (data.household.timers.length) timers.replaceChildren();
  for (const timer of data.household.timers) {
    const card = make('article',undefined,'timer-row');
    const copy = make('div'); copy.append(make('b',timer.name),make('p',timer.state + (timer.elapsed_while_stopped ? ' · elapsed while Luma was stopped' : '')));
    const clock = make('strong',formatTime(timer.remaining_seconds),'timer-count');
    if (timer.state==='running') clock.dataset.ends=timer.ends_at;
    card.append(copy,clock);
    const controls = make('div',undefined,'row-controls');
    for (const action of timer.state==='running'?['pause','cancel']:timer.state==='paused'?['resume','cancel']:['acknowledge']) controls.append(button(action,async()=>{result(await api('/api/timers/control',{id:timer.id,action}));await refresh();}));
    card.append(controls); timers.append(card);
  }
  const recipes = $('#recipe-list'); empty(recipes,'Save a recipe, then say “next step” as you cook.');
  if (data.household.recipes.length) recipes.replaceChildren();
  for (const recipe of data.household.recipes) {
    const card = make('article',undefined,'receipt');
    card.append(make('span',recipe.state+' · '+recipe.step_number+' / '+recipe.step_count,'eyebrow'),make('h3',recipe.title),make('p',recipe.current_step));
    for (const action of recipe.state==='cooking'?['back','repeat','next','pause','finish']:recipe.state==='paused'?['resume','finish']:['start']) card.append(button(action,async()=>{result(await api('/api/recipes/action',{id:recipe.id,action}));await refresh();}));
    if (adult) card.append(button('Edit',async()=>{
      $('#recipe-id').value=recipe.id; $('#recipe-title').value=recipe.title; $('#recipe-steps').value=recipe.steps.join('\n');$('#recipe-source').value=recipe.source_url||'';$('#recipe-title').focus();
    }),button('Remove',async()=>{await api('/api/recipes/delete',{id:recipe.id});await refresh();}));
    recipes.append(card);
  }
  renderHousehold(data.household.records);
  const workflows = $('#workflow-list'); empty(workflows,'Your task progress and verified steps will stay here.');
  if (data.workflows.length) workflows.replaceChildren();
  for (const run of data.workflows) {
    const card=make('article',undefined,'receipt');
    card.append(make('span',run.state.replaceAll('_',' '),'eyebrow'),make('h3',run.goal));
    for (const [index,step] of run.steps.entries()) card.append(make('p',`${index+1}. ${step.tool.replaceAll('.',' · ')} — ${step.state}`));
    card.append(make('p',run.summary));
    if (!['running','stopped'].includes(run.state)) card.append(button('Continue or revise',async()=>{
      $('#agent-resume-id').value=run.id; $('#agent-goal').value='Continue the remaining steps of this task.';$('#agent-submit').textContent='Continue agent task ↗';$('#agent-goal').focus();
    }));
    if (run.state!=='stopped') card.append(button('Stop task',async()=>{await api('/api/workflows/stop',{id:run.id});await refresh();}));
    workflows.append(card);
  }
  const lists=$('#local-grocery-lists'); lists.replaceChildren();
  for (const list of data.local_grocery_lists) {
    const card=make('article',undefined,'receipt'); card.append(make('span','SAVED LOCALLY · NO ORDER PLACED','eyebrow'),make('h3',list.title));
    for (const item of list.items) card.append(make('p',`${item.quantity} ${item.unit} · ${item.name}`));
    const recipient=make('input');recipient.placeholder='Mom or exact phone number';recipient.setAttribute('aria-label','Grocery message recipient');recipient.setAttribute('list','contact-options');recipient.className='recipient-input';card.append(recipient);
    card.append(button('Prepare family text',async()=>{result(await api('/api/groceries/family',{id:list.id,recipient:recipient.value}));await refresh();$('#results').scrollIntoView({behavior:'smooth'});}),button('Edit list',async()=>{
      $('#grocery-local-id').value=list.id;$('#grocery-title').value=list.title;$('#grocery-items').replaceChildren();for(const item of list.items)addGroceryItem(item.name,item.quantity,item.unit);$('#grocery-title').focus();
    }),button('Remove',async()=>{await api('/api/groceries/delete',{id:list.id});await refresh();}));lists.append(card);
  }
}
function formatTime(seconds) {
  const value=Math.max(0,Math.ceil(seconds||0));
  return `${Math.floor(value/60)}:${String(value%60).padStart(2,'0')}`;
}
setInterval(()=>{for(const clock of document.querySelectorAll('[data-ends]'))clock.textContent=formatTime(Number(clock.dataset.ends)-Date.now()/1000);},1000);

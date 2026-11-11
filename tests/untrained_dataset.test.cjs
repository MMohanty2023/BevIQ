const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname,'..','templates','index.html'),'utf8');
const block = html.match(/\/\/ Untrained dataset loader([\s\S]*?)\/\/ End untrained dataset loader/);
assert.ok(block,'Untrained loader with summary handling is required');

function setup(fetchData) {
    const nodes = Object.fromEntries(['untrained-brand-search','untrained-total-records','untrained-total-brands','untrained-record-count'].map(id=>[id,{value:'',textContent:'—'}]));
    const table={innerHTML:''};
    const context=vm.createContext({
        document:{getElementById:id=>nodes[id],querySelector:()=>table},
        URLSearchParams,
        getDashboardData:fetchData,
        escapeHtml:value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'),
        untrainedDatasetLoaded:true,
    });
    vm.runInContext(block[1],context);
    return {context,nodes,table};
}

test('cards show totals before pagination rather than displayed row count',async()=>{
    const {context,nodes,table}=setup(async()=>({
        summary:{total_records:1200,unique_untrained_brands:80},
        records:[{brand_name:'Alpha',category:'Beer',source:'beer.csv'}],
    }));
    await context.loadUntrainedDataset();
    assert.equal(nodes['untrained-total-records'].textContent,'1,200');
    assert.equal(nodes['untrained-total-brands'].textContent,'80');
    assert.match(nodes['untrained-record-count'].textContent,/1 of 1,200/);
    assert.match(table.innerHTML,/Alpha/);
});

test('a valid empty result shows zero counts',async()=>{
    const {context,nodes,table}=setup(async()=>({
        summary:{total_records:0,unique_untrained_brands:0},records:[],
    }));
    await context.loadUntrainedDataset();
    assert.equal(nodes['untrained-total-records'].textContent,'0');
    assert.equal(nodes['untrained-total-brands'].textContent,'0');
    assert.match(table.innerHTML,/No new brands found/);
});

test('request failure is visible and clears stale totals',async()=>{
    const {context,nodes,table}=setup(async()=>{throw new Error('Service unavailable');});
    await context.loadUntrainedDataset();
    assert.equal(nodes['untrained-total-records'].textContent,'—');
    assert.match(nodes['untrained-record-count'].textContent,/Could not load/);
    assert.match(table.innerHTML,/Service unavailable/);
    assert.equal(context.untrainedDatasetLoaded,false);
});

test('a late old search cannot overwrite the newest search counts',async()=>{
    const pending=[];
    const {context,nodes}=setup(url=>new Promise(resolve=>pending.push({url,resolve})));
    nodes['untrained-brand-search'].value='alpha';
    const first=context.loadUntrainedDataset();
    nodes['untrained-brand-search'].value='beta';
    const second=context.loadUntrainedDataset();
    pending[1].resolve({summary:{total_records:2,unique_untrained_brands:1},records:[]});
    await second;
    pending[0].resolve({summary:{total_records:999,unique_untrained_brands:99},records:[]});
    await first;
    assert.equal(nodes['untrained-total-records'].textContent,'2');
    assert.ok(pending[1].url.includes('search=beta'));
});

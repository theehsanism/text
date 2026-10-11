import glob,os,json,collections,lxml.html,re
from urllib.parse import urlparse
M='manual';OUT='data/knowledge-graph';os.makedirs(OUT,exist_ok=True)
fs=sorted(glob.glob(M+'/*/**/*.html',recursive=True))
byname={os.path.basename(f):f for f in fs}
nodes=[];edges=[];typec=collections.Counter();sig=collections.defaultdict(collections.Counter)
cls_all=collections.Counter();tag_all=collections.Counter();class_type=collections.defaultdict(collections.Counter)
def tgt(h):
    if not h or h.startswith(('http:','https:','mailto:','#','javascript:')):return None
    b=os.path.basename(urlparse(h).path)
    return b if b in byname else None
for f in fs:
    t=lxml.html.parse(f);pid=os.path.basename(f)[:-5]
    r=t.xpath('/html/body/div[3]/div/div')[0]
    ptype=(r.get('class') or 'root').split()[0]
    tags=collections.Counter();cls=collections.Counter()
    for e in r.iter():
        if not isinstance(e.tag,str):continue
        tags[e.tag]+=1
        for c in (e.get('class') or '').split(): cls[c]+=1
    children=[{'tag':c.tag,'class':c.get('class'),'id':c.get('id')} for c in r if isinstance(c.tag,str)]
    ss=[ (c['class'] or c['tag']).replace('refsect1 ','') for c in children]
    sig[ptype][' > '.join(ss)]+=1
    h=r.xpath('.//h1|.//h2');title=re.sub(r'\s+',' ',h[0].text_content()).strip() if h else pid
    rn=r.xpath('.//*[@class="refpurpose"]');purpose=re.sub(r'\s+',' ',rn[0].text_content()).strip() if rn else None
    links=collections.Counter()
    for a in r.iter('a'):
        b=tgt(a.get('href'))
        if b and b[:-5]!=pid: links[b[:-5]]+=1
    for b,n in links.items(): edges.append({'source':pid,'target':b,'type':'links_to','weight':n})
    bc=t.xpath('//ul[@id="breadcrumbs-inner"]//a/@href') or t.xpath('//*[@id="breadcrumbs"]//a/@href')
    bc=[x for x in (tgt(h) for h in bc) if x]
    if bc and bc[-1][:-5]!=pid: edges.append({'source':pid,'target':bc[-1][:-5],'type':'child_of','weight':1})
    typec[ptype]+=1;cls_all.update(cls);tag_all.update(tags)
    for c in cls: class_type[c][ptype]+=1
    nodes.append({'id':pid,'type':ptype,'section':f.split('/')[1],'path':f,'title':title,'purpose':purpose,
      'children':children,'tags':dict(tags),'classes':dict(cls),'out_links':len(links)})
json.dump(nodes,open(OUT+'/nodes.json','w'),ensure_ascii=False)
json.dump(edges,open(OUT+'/edges.json','w'),ensure_ascii=False)
# ontology: page types, their canonical child structure, class->type
ont={'xpath':'/html/body/div[3]/div/div','formula':'tags + classes + links + children',
 'page_types':{k:{'pages':v,'top_child_structures':sig[k].most_common(8)} for k,v in typec.most_common()},
 'classes':{c:{'count':n,'page_types':dict(class_type[c])} for c,n in cls_all.most_common()},
 'tags':dict(tag_all.most_common())}
json.dump(ont,open(OUT+'/ontology.json','w'),ensure_ascii=False,indent=1)
ec=collections.Counter(e['type'] for e in edges)
print(len(nodes),dict(ec),len(cls_all))
for k in typec: print(k,sig[k].most_common(2))

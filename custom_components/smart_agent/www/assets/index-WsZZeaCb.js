(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const e of document.querySelectorAll('link[rel="modulepreload"]'))s(e);new MutationObserver(e=>{for(const r of e)if(r.type==="childList")for(const o of r.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&s(o)}).observe(document,{childList:!0,subtree:!0});function i(e){const r={};return e.integrity&&(r.integrity=e.integrity),e.referrerPolicy&&(r.referrerPolicy=e.referrerPolicy),e.crossOrigin==="use-credentials"?r.credentials="include":e.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function s(e){if(e.ep)return;e.ep=!0;const r=i(e);fetch(e.href,r)}})();/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Rt=globalThis,Ce=Rt.ShadowRoot&&(Rt.ShadyCSS===void 0||Rt.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Ae=Symbol(),De=new WeakMap;let Ei=class{constructor(t,i,s){if(this._$cssResult$=!0,s!==Ae)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=i}get styleSheet(){let t=this.o;const i=this.t;if(Ce&&t===void 0){const s=i!==void 0&&i.length===1;s&&(t=De.get(i)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&De.set(i,t))}return t}toString(){return this.cssText}};const Ui=n=>new Ei(typeof n=="string"?n:n+"",void 0,Ae),B=(n,...t)=>{const i=n.length===1?n[0]:t.reduce((s,e,r)=>s+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(e)+n[r+1],n[0]);return new Ei(i,n,Ae)},ji=(n,t)=>{if(Ce)n.adoptedStyleSheets=t.map(i=>i instanceof CSSStyleSheet?i:i.styleSheet);else for(const i of t){const s=document.createElement("style"),e=Rt.litNonce;e!==void 0&&s.setAttribute("nonce",e),s.textContent=i.cssText,n.appendChild(s)}},ze=Ce?n=>n:n=>n instanceof CSSStyleSheet?(t=>{let i="";for(const s of t.cssRules)i+=s.cssText;return Ui(i)})(n):n;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:Hi,defineProperty:qi,getOwnPropertyDescriptor:Vi,getOwnPropertyNames:Ji,getOwnPropertySymbols:Yi,getPrototypeOf:Ki}=Object,Y=globalThis,Be=Y.trustedTypes,Wi=Be?Be.emptyScript:"",Qt=Y.reactiveElementPolyfillSupport,vt=(n,t)=>n,Mt={toAttribute(n,t){switch(t){case Boolean:n=n?Wi:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,t){let i=n;switch(t){case Boolean:i=n!==null;break;case Number:i=n===null?null:Number(n);break;case Object:case Array:try{i=JSON.parse(n)}catch{i=null}}return i}},ke=(n,t)=>!Hi(n,t),Ne={attribute:!0,type:String,converter:Mt,reflect:!1,useDefault:!1,hasChanged:ke};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),Y.litPropertyMetadata??(Y.litPropertyMetadata=new WeakMap);let nt=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??(this.l=[])).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,i=Ne){if(i.state&&(i.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((i=Object.create(i)).wrapped=!0),this.elementProperties.set(t,i),!i.noAccessor){const s=Symbol(),e=this.getPropertyDescriptor(t,s,i);e!==void 0&&qi(this.prototype,t,e)}}static getPropertyDescriptor(t,i,s){const{get:e,set:r}=Vi(this.prototype,t)??{get(){return this[i]},set(o){this[i]=o}};return{get:e,set(o){const l=e==null?void 0:e.call(this);r==null||r.call(this,o),this.requestUpdate(t,l,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Ne}static _$Ei(){if(this.hasOwnProperty(vt("elementProperties")))return;const t=Ki(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(vt("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(vt("properties"))){const i=this.properties,s=[...Ji(i),...Yi(i)];for(const e of s)this.createProperty(e,i[e])}const t=this[Symbol.metadata];if(t!==null){const i=litPropertyMetadata.get(t);if(i!==void 0)for(const[s,e]of i)this.elementProperties.set(s,e)}this._$Eh=new Map;for(const[i,s]of this.elementProperties){const e=this._$Eu(i,s);e!==void 0&&this._$Eh.set(e,i)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const i=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const e of s)i.unshift(ze(e))}else t!==void 0&&i.push(ze(t));return i}static _$Eu(t,i){const s=i.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var t;this._$ES=new Promise(i=>this.enableUpdating=i),this._$AL=new Map,this._$E_(),this.requestUpdate(),(t=this.constructor.l)==null||t.forEach(i=>i(this))}addController(t){var i;(this._$EO??(this._$EO=new Set)).add(t),this.renderRoot!==void 0&&this.isConnected&&((i=t.hostConnected)==null||i.call(t))}removeController(t){var i;(i=this._$EO)==null||i.delete(t)}_$E_(){const t=new Map,i=this.constructor.elementProperties;for(const s of i.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ji(t,this.constructor.elementStyles),t}connectedCallback(){var t;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(t=this._$EO)==null||t.forEach(i=>{var s;return(s=i.hostConnected)==null?void 0:s.call(i)})}enableUpdating(t){}disconnectedCallback(){var t;(t=this._$EO)==null||t.forEach(i=>{var s;return(s=i.hostDisconnected)==null?void 0:s.call(i)})}attributeChangedCallback(t,i,s){this._$AK(t,s)}_$ET(t,i){var r;const s=this.constructor.elementProperties.get(t),e=this.constructor._$Eu(t,s);if(e!==void 0&&s.reflect===!0){const o=(((r=s.converter)==null?void 0:r.toAttribute)!==void 0?s.converter:Mt).toAttribute(i,s.type);this._$Em=t,o==null?this.removeAttribute(e):this.setAttribute(e,o),this._$Em=null}}_$AK(t,i){var r,o;const s=this.constructor,e=s._$Eh.get(t);if(e!==void 0&&this._$Em!==e){const l=s.getPropertyOptions(e),a=typeof l.converter=="function"?{fromAttribute:l.converter}:((r=l.converter)==null?void 0:r.fromAttribute)!==void 0?l.converter:Mt;this._$Em=e;const d=a.fromAttribute(i,l.type);this[e]=d??((o=this._$Ej)==null?void 0:o.get(e))??d,this._$Em=null}}requestUpdate(t,i,s,e=!1,r){var o;if(t!==void 0){const l=this.constructor;if(e===!1&&(r=this[t]),s??(s=l.getPropertyOptions(t)),!((s.hasChanged??ke)(r,i)||s.useDefault&&s.reflect&&r===((o=this._$Ej)==null?void 0:o.get(t))&&!this.hasAttribute(l._$Eu(t,s))))return;this.C(t,i,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,i,{useDefault:s,reflect:e,wrapped:r},o){s&&!(this._$Ej??(this._$Ej=new Map)).has(t)&&(this._$Ej.set(t,o??i??this[t]),r!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(i=void 0),this._$AL.set(t,i)),e===!0&&this._$Em!==t&&(this._$Eq??(this._$Eq=new Set)).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(i){Promise.reject(i)}const t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var s;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[r,o]of this._$Ep)this[r]=o;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[r,o]of e){const{wrapped:l}=o,a=this[r];l!==!0||this._$AL.has(r)||a===void 0||this.C(r,void 0,o,a)}}let t=!1;const i=this._$AL;try{t=this.shouldUpdate(i),t?(this.willUpdate(i),(s=this._$EO)==null||s.forEach(e=>{var r;return(r=e.hostUpdate)==null?void 0:r.call(e)}),this.update(i)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(i)}willUpdate(t){}_$AE(t){var i;(i=this._$EO)==null||i.forEach(s=>{var e;return(e=s.hostUpdated)==null?void 0:e.call(s)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&(this._$Eq=this._$Eq.forEach(i=>this._$ET(i,this[i]))),this._$EM()}updated(t){}firstUpdated(t){}};nt.elementStyles=[],nt.shadowRootOptions={mode:"open"},nt[vt("elementProperties")]=new Map,nt[vt("finalized")]=new Map,Qt==null||Qt({ReactiveElement:nt}),(Y.reactiveElementVersions??(Y.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const bt=globalThis,Le=n=>n,It=bt.trustedTypes,Fe=It?It.createPolicy("lit-html",{createHTML:n=>n}):void 0,Si="$lit$",J=`lit$${Math.random().toFixed(9).slice(2)}$`,$i="?"+J,Gi=`<${$i}>`,Q=document,yt=()=>Q.createComment(""),_t=n=>n===null||typeof n!="object"&&typeof n!="function",Pe=Array.isArray,Xi=n=>Pe(n)||typeof(n==null?void 0:n[Symbol.iterator])=="function",Zt=`[ 	
\f\r]`,ft=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ue=/-->/g,je=/>/g,K=RegExp(`>|${Zt}(?:([^\\s"'>=/]+)(${Zt}*=${Zt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),He=/'/g,qe=/"/g,Ci=/^(?:script|style|textarea|title)$/i,Qi=n=>(t,...i)=>({_$litType$:n,strings:t,values:i}),g=Qi(1),at=Symbol.for("lit-noChange"),L=Symbol.for("lit-nothing"),Ve=new WeakMap,G=Q.createTreeWalker(Q,129);function Ai(n,t){if(!Pe(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return Fe!==void 0?Fe.createHTML(t):t}const Zi=(n,t)=>{const i=n.length-1,s=[];let e,r=t===2?"<svg>":t===3?"<math>":"",o=ft;for(let l=0;l<i;l++){const a=n[l];let d,h,c=-1,p=0;for(;p<a.length&&(o.lastIndex=p,h=o.exec(a),h!==null);)p=o.lastIndex,o===ft?h[1]==="!--"?o=Ue:h[1]!==void 0?o=je:h[2]!==void 0?(Ci.test(h[2])&&(e=RegExp("</"+h[2],"g")),o=K):h[3]!==void 0&&(o=K):o===K?h[0]===">"?(o=e??ft,c=-1):h[1]===void 0?c=-2:(c=o.lastIndex-h[2].length,d=h[1],o=h[3]===void 0?K:h[3]==='"'?qe:He):o===qe||o===He?o=K:o===Ue||o===je?o=ft:(o=K,e=void 0);const u=o===K&&n[l+1].startsWith("/>")?" ":"";r+=o===ft?a+Gi:c>=0?(s.push(d),a.slice(0,c)+Si+a.slice(c)+J+u):a+J+(c===-2?l:u)}return[Ai(n,r+(n[i]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]};class xt{constructor({strings:t,_$litType$:i},s){let e;this.parts=[];let r=0,o=0;const l=t.length-1,a=this.parts,[d,h]=Zi(t,i);if(this.el=xt.createElement(d,s),G.currentNode=this.el.content,i===2||i===3){const c=this.el.content.firstChild;c.replaceWith(...c.childNodes)}for(;(e=G.nextNode())!==null&&a.length<l;){if(e.nodeType===1){if(e.hasAttributes())for(const c of e.getAttributeNames())if(c.endsWith(Si)){const p=h[o++],u=e.getAttribute(c).split(J),v=/([.?@])?(.*)/.exec(p);a.push({type:1,index:r,name:v[2],strings:u,ctor:v[1]==="."?es:v[1]==="?"?is:v[1]==="@"?ss:Ht}),e.removeAttribute(c)}else c.startsWith(J)&&(a.push({type:6,index:r}),e.removeAttribute(c));if(Ci.test(e.tagName)){const c=e.textContent.split(J),p=c.length-1;if(p>0){e.textContent=It?It.emptyScript:"";for(let u=0;u<p;u++)e.append(c[u],yt()),G.nextNode(),a.push({type:2,index:++r});e.append(c[p],yt())}}}else if(e.nodeType===8)if(e.data===$i)a.push({type:2,index:r});else{let c=-1;for(;(c=e.data.indexOf(J,c+1))!==-1;)a.push({type:7,index:r}),c+=J.length-1}r++}}static createElement(t,i){const s=Q.createElement("template");return s.innerHTML=t,s}}function lt(n,t,i=n,s){var o,l;if(t===at)return t;let e=s!==void 0?(o=i._$Co)==null?void 0:o[s]:i._$Cl;const r=_t(t)?void 0:t._$litDirective$;return(e==null?void 0:e.constructor)!==r&&((l=e==null?void 0:e._$AO)==null||l.call(e,!1),r===void 0?e=void 0:(e=new r(n),e._$AT(n,i,s)),s!==void 0?(i._$Co??(i._$Co=[]))[s]=e:i._$Cl=e),e!==void 0&&(t=lt(n,e._$AS(n,t.values),e,s)),t}class ts{constructor(t,i){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=i}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:i},parts:s}=this._$AD,e=((t==null?void 0:t.creationScope)??Q).importNode(i,!0);G.currentNode=e;let r=G.nextNode(),o=0,l=0,a=s[0];for(;a!==void 0;){if(o===a.index){let d;a.type===2?d=new At(r,r.nextSibling,this,t):a.type===1?d=new a.ctor(r,a.name,a.strings,this,t):a.type===6&&(d=new ns(r,this,t)),this._$AV.push(d),a=s[++l]}o!==(a==null?void 0:a.index)&&(r=G.nextNode(),o++)}return G.currentNode=Q,e}p(t){let i=0;for(const s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,i),i+=s.strings.length-2):s._$AI(t[i])),i++}}class At{get _$AU(){var t;return((t=this._$AM)==null?void 0:t._$AU)??this._$Cv}constructor(t,i,s,e){this.type=2,this._$AH=L,this._$AN=void 0,this._$AA=t,this._$AB=i,this._$AM=s,this.options=e,this._$Cv=(e==null?void 0:e.isConnected)??!0}get parentNode(){let t=this._$AA.parentNode;const i=this._$AM;return i!==void 0&&(t==null?void 0:t.nodeType)===11&&(t=i.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,i=this){t=lt(this,t,i),_t(t)?t===L||t==null||t===""?(this._$AH!==L&&this._$AR(),this._$AH=L):t!==this._$AH&&t!==at&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Xi(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==L&&_t(this._$AH)?this._$AA.nextSibling.data=t:this.T(Q.createTextNode(t)),this._$AH=t}$(t){var r;const{values:i,_$litType$:s}=t,e=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=xt.createElement(Ai(s.h,s.h[0]),this.options)),s);if(((r=this._$AH)==null?void 0:r._$AD)===e)this._$AH.p(i);else{const o=new ts(e,this),l=o.u(this.options);o.p(i),this.T(l),this._$AH=o}}_$AC(t){let i=Ve.get(t.strings);return i===void 0&&Ve.set(t.strings,i=new xt(t)),i}k(t){Pe(this._$AH)||(this._$AH=[],this._$AR());const i=this._$AH;let s,e=0;for(const r of t)e===i.length?i.push(s=new At(this.O(yt()),this.O(yt()),this,this.options)):s=i[e],s._$AI(r),e++;e<i.length&&(this._$AR(s&&s._$AB.nextSibling,e),i.length=e)}_$AR(t=this._$AA.nextSibling,i){var s;for((s=this._$AP)==null?void 0:s.call(this,!1,!0,i);t!==this._$AB;){const e=Le(t).nextSibling;Le(t).remove(),t=e}}setConnected(t){var i;this._$AM===void 0&&(this._$Cv=t,(i=this._$AP)==null||i.call(this,t))}}class Ht{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,i,s,e,r){this.type=1,this._$AH=L,this._$AN=void 0,this.element=t,this.name=i,this._$AM=e,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=L}_$AI(t,i=this,s,e){const r=this.strings;let o=!1;if(r===void 0)t=lt(this,t,i,0),o=!_t(t)||t!==this._$AH&&t!==at,o&&(this._$AH=t);else{const l=t;let a,d;for(t=r[0],a=0;a<r.length-1;a++)d=lt(this,l[s+a],i,a),d===at&&(d=this._$AH[a]),o||(o=!_t(d)||d!==this._$AH[a]),d===L?t=L:t!==L&&(t+=(d??"")+r[a+1]),this._$AH[a]=d}o&&!e&&this.j(t)}j(t){t===L?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class es extends Ht{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===L?void 0:t}}class is extends Ht{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==L)}}class ss extends Ht{constructor(t,i,s,e,r){super(t,i,s,e,r),this.type=5}_$AI(t,i=this){if((t=lt(this,t,i,0)??L)===at)return;const s=this._$AH,e=t===L&&s!==L||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,r=t!==L&&(s===L||e);e&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){var i;typeof this._$AH=="function"?this._$AH.call(((i=this.options)==null?void 0:i.host)??this.element,t):this._$AH.handleEvent(t)}}class ns{constructor(t,i,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=i,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){lt(this,t)}}const te=bt.litHtmlPolyfillSupport;te==null||te(xt,At),(bt.litHtmlVersions??(bt.litHtmlVersions=[])).push("3.3.2");const rs=(n,t,i)=>{const s=(i==null?void 0:i.renderBefore)??t;let e=s._$litPart$;if(e===void 0){const r=(i==null?void 0:i.renderBefore)??null;s._$litPart$=e=new At(t.insertBefore(yt(),r),r,void 0,i??{})}return e._$AI(n),e};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const X=globalThis;class D extends nt{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var i;const t=super.createRenderRoot();return(i=this.renderOptions).renderBefore??(i.renderBefore=t.firstChild),t}update(t){const i=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=rs(i,this.renderRoot,this.renderOptions)}connectedCallback(){var t;super.connectedCallback(),(t=this._$Do)==null||t.setConnected(!0)}disconnectedCallback(){var t;super.disconnectedCallback(),(t=this._$Do)==null||t.setConnected(!1)}render(){return at}}var wi;D._$litElement$=!0,D.finalized=!0,(wi=X.litElementHydrateSupport)==null||wi.call(X,{LitElement:D});const ee=X.litElementPolyfillSupport;ee==null||ee({LitElement:D});(X.litElementVersions??(X.litElementVersions=[])).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const N=n=>(t,i)=>{i!==void 0?i.addInitializer(()=>{customElements.define(n,t)}):customElements.define(n,t)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const os={attribute:!0,type:String,converter:Mt,reflect:!1,hasChanged:ke},as=(n=os,t,i)=>{const{kind:s,metadata:e}=i;let r=globalThis.litPropertyMetadata.get(e);if(r===void 0&&globalThis.litPropertyMetadata.set(e,r=new Map),s==="setter"&&((n=Object.create(n)).wrapped=!0),r.set(i.name,n),s==="accessor"){const{name:o}=i;return{set(l){const a=t.get.call(this);t.set.call(this,l),this.requestUpdate(o,a,n,!0,l)},init(l){return l!==void 0&&this.C(o,void 0,n,l),l}}}if(s==="setter"){const{name:o}=i;return function(l){const a=this[o];t.call(this,l),this.requestUpdate(o,a,n,!0,l)}}throw Error("Unsupported decorator location: "+s)};function T(n){return(t,i)=>typeof i=="object"?as(n,t,i):((s,e,r)=>{const o=e.hasOwnProperty(r);return e.constructor.createProperty(r,s),o?Object.getOwnPropertyDescriptor(e,r):void 0})(n,t,i)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function M(n){return T({...n,state:!0,attribute:!1})}function ls(n){return n&&n.__esModule&&Object.prototype.hasOwnProperty.call(n,"default")?n.default:n}var st={},ie,Je;function cs(){return Je||(Je=1,ie=function(){return typeof Promise=="function"&&Promise.prototype&&Promise.prototype.then}),ie}var se={},V={},Ye;function tt(){if(Ye)return V;Ye=1;let n;const t=[0,26,44,70,100,134,172,196,242,292,346,404,466,532,581,655,733,815,901,991,1085,1156,1258,1364,1474,1588,1706,1828,1921,2051,2185,2323,2465,2611,2761,2876,3034,3196,3362,3532,3706];return V.getSymbolSize=function(s){if(!s)throw new Error('"version" cannot be null or undefined');if(s<1||s>40)throw new Error('"version" should be in range from 1 to 40');return s*4+17},V.getSymbolTotalCodewords=function(s){return t[s]},V.getBCHDigit=function(i){let s=0;for(;i!==0;)s++,i>>>=1;return s},V.setToSJISFunction=function(s){if(typeof s!="function")throw new Error('"toSJISFunc" is not a valid function.');n=s},V.isKanjiModeEnabled=function(){return typeof n<"u"},V.toSJIS=function(s){return n(s)},V}var ne={},Ke;function Te(){return Ke||(Ke=1,(function(n){n.L={bit:1},n.M={bit:0},n.Q={bit:3},n.H={bit:2};function t(i){if(typeof i!="string")throw new Error("Param is not a string");switch(i.toLowerCase()){case"l":case"low":return n.L;case"m":case"medium":return n.M;case"q":case"quartile":return n.Q;case"h":case"high":return n.H;default:throw new Error("Unknown EC Level: "+i)}}n.isValid=function(s){return s&&typeof s.bit<"u"&&s.bit>=0&&s.bit<4},n.from=function(s,e){if(n.isValid(s))return s;try{return t(s)}catch{return e}}})(ne)),ne}var re,We;function ds(){if(We)return re;We=1;function n(){this.buffer=[],this.length=0}return n.prototype={get:function(t){const i=Math.floor(t/8);return(this.buffer[i]>>>7-t%8&1)===1},put:function(t,i){for(let s=0;s<i;s++)this.putBit((t>>>i-s-1&1)===1)},getLengthInBits:function(){return this.length},putBit:function(t){const i=Math.floor(this.length/8);this.buffer.length<=i&&this.buffer.push(0),t&&(this.buffer[i]|=128>>>this.length%8),this.length++}},re=n,re}var oe,Ge;function hs(){if(Ge)return oe;Ge=1;function n(t){if(!t||t<1)throw new Error("BitMatrix size must be defined and greater than 0");this.size=t,this.data=new Uint8Array(t*t),this.reservedBit=new Uint8Array(t*t)}return n.prototype.set=function(t,i,s,e){const r=t*this.size+i;this.data[r]=s,e&&(this.reservedBit[r]=!0)},n.prototype.get=function(t,i){return this.data[t*this.size+i]},n.prototype.xor=function(t,i,s){this.data[t*this.size+i]^=s},n.prototype.isReserved=function(t,i){return this.reservedBit[t*this.size+i]},oe=n,oe}var ae={},Xe;function ps(){return Xe||(Xe=1,(function(n){const t=tt().getSymbolSize;n.getRowColCoords=function(s){if(s===1)return[];const e=Math.floor(s/7)+2,r=t(s),o=r===145?26:Math.ceil((r-13)/(2*e-2))*2,l=[r-7];for(let a=1;a<e-1;a++)l[a]=l[a-1]-o;return l.push(6),l.reverse()},n.getPositions=function(s){const e=[],r=n.getRowColCoords(s),o=r.length;for(let l=0;l<o;l++)for(let a=0;a<o;a++)l===0&&a===0||l===0&&a===o-1||l===o-1&&a===0||e.push([r[l],r[a]]);return e}})(ae)),ae}var le={},Qe;function us(){if(Qe)return le;Qe=1;const n=tt().getSymbolSize,t=7;return le.getPositions=function(s){const e=n(s);return[[0,0],[e-t,0],[0,e-t]]},le}var ce={},Ze;function gs(){return Ze||(Ze=1,(function(n){n.Patterns={PATTERN000:0,PATTERN001:1,PATTERN010:2,PATTERN011:3,PATTERN100:4,PATTERN101:5,PATTERN110:6,PATTERN111:7};const t={N1:3,N2:3,N3:40,N4:10};n.isValid=function(e){return e!=null&&e!==""&&!isNaN(e)&&e>=0&&e<=7},n.from=function(e){return n.isValid(e)?parseInt(e,10):void 0},n.getPenaltyN1=function(e){const r=e.size;let o=0,l=0,a=0,d=null,h=null;for(let c=0;c<r;c++){l=a=0,d=h=null;for(let p=0;p<r;p++){let u=e.get(c,p);u===d?l++:(l>=5&&(o+=t.N1+(l-5)),d=u,l=1),u=e.get(p,c),u===h?a++:(a>=5&&(o+=t.N1+(a-5)),h=u,a=1)}l>=5&&(o+=t.N1+(l-5)),a>=5&&(o+=t.N1+(a-5))}return o},n.getPenaltyN2=function(e){const r=e.size;let o=0;for(let l=0;l<r-1;l++)for(let a=0;a<r-1;a++){const d=e.get(l,a)+e.get(l,a+1)+e.get(l+1,a)+e.get(l+1,a+1);(d===4||d===0)&&o++}return o*t.N2},n.getPenaltyN3=function(e){const r=e.size;let o=0,l=0,a=0;for(let d=0;d<r;d++){l=a=0;for(let h=0;h<r;h++)l=l<<1&2047|e.get(d,h),h>=10&&(l===1488||l===93)&&o++,a=a<<1&2047|e.get(h,d),h>=10&&(a===1488||a===93)&&o++}return o*t.N3},n.getPenaltyN4=function(e){let r=0;const o=e.data.length;for(let a=0;a<o;a++)r+=e.data[a];return Math.abs(Math.ceil(r*100/o/5)-10)*t.N4};function i(s,e,r){switch(s){case n.Patterns.PATTERN000:return(e+r)%2===0;case n.Patterns.PATTERN001:return e%2===0;case n.Patterns.PATTERN010:return r%3===0;case n.Patterns.PATTERN011:return(e+r)%3===0;case n.Patterns.PATTERN100:return(Math.floor(e/2)+Math.floor(r/3))%2===0;case n.Patterns.PATTERN101:return e*r%2+e*r%3===0;case n.Patterns.PATTERN110:return(e*r%2+e*r%3)%2===0;case n.Patterns.PATTERN111:return(e*r%3+(e+r)%2)%2===0;default:throw new Error("bad maskPattern:"+s)}}n.applyMask=function(e,r){const o=r.size;for(let l=0;l<o;l++)for(let a=0;a<o;a++)r.isReserved(a,l)||r.xor(a,l,i(e,a,l))},n.getBestMask=function(e,r){const o=Object.keys(n.Patterns).length;let l=0,a=1/0;for(let d=0;d<o;d++){r(d),n.applyMask(d,e);const h=n.getPenaltyN1(e)+n.getPenaltyN2(e)+n.getPenaltyN3(e)+n.getPenaltyN4(e);n.applyMask(d,e),h<a&&(a=h,l=d)}return l}})(ce)),ce}var Tt={},ti;function ki(){if(ti)return Tt;ti=1;const n=Te(),t=[1,1,1,1,1,1,1,1,1,1,2,2,1,2,2,4,1,2,4,4,2,4,4,4,2,4,6,5,2,4,6,6,2,5,8,8,4,5,8,8,4,5,8,11,4,8,10,11,4,9,12,16,4,9,16,16,6,10,12,18,6,10,17,16,6,11,16,19,6,13,18,21,7,14,21,25,8,16,20,25,8,17,23,25,9,17,23,34,9,18,25,30,10,20,27,32,12,21,29,35,12,23,34,37,12,25,34,40,13,26,35,42,14,28,38,45,15,29,40,48,16,31,43,51,17,33,45,54,18,35,48,57,19,37,51,60,19,38,53,63,20,40,56,66,21,43,59,70,22,45,62,74,24,47,65,77,25,49,68,81],i=[7,10,13,17,10,16,22,28,15,26,36,44,20,36,52,64,26,48,72,88,36,64,96,112,40,72,108,130,48,88,132,156,60,110,160,192,72,130,192,224,80,150,224,264,96,176,260,308,104,198,288,352,120,216,320,384,132,240,360,432,144,280,408,480,168,308,448,532,180,338,504,588,196,364,546,650,224,416,600,700,224,442,644,750,252,476,690,816,270,504,750,900,300,560,810,960,312,588,870,1050,336,644,952,1110,360,700,1020,1200,390,728,1050,1260,420,784,1140,1350,450,812,1200,1440,480,868,1290,1530,510,924,1350,1620,540,980,1440,1710,570,1036,1530,1800,570,1064,1590,1890,600,1120,1680,1980,630,1204,1770,2100,660,1260,1860,2220,720,1316,1950,2310,750,1372,2040,2430];return Tt.getBlocksCount=function(e,r){switch(r){case n.L:return t[(e-1)*4+0];case n.M:return t[(e-1)*4+1];case n.Q:return t[(e-1)*4+2];case n.H:return t[(e-1)*4+3];default:return}},Tt.getTotalCodewordsCount=function(e,r){switch(r){case n.L:return i[(e-1)*4+0];case n.M:return i[(e-1)*4+1];case n.Q:return i[(e-1)*4+2];case n.H:return i[(e-1)*4+3];default:return}},Tt}var de={},mt={},ei;function fs(){if(ei)return mt;ei=1;const n=new Uint8Array(512),t=new Uint8Array(256);return(function(){let s=1;for(let e=0;e<255;e++)n[e]=s,t[s]=e,s<<=1,s&256&&(s^=285);for(let e=255;e<512;e++)n[e]=n[e-255]})(),mt.log=function(s){if(s<1)throw new Error("log("+s+")");return t[s]},mt.exp=function(s){return n[s]},mt.mul=function(s,e){return s===0||e===0?0:n[t[s]+t[e]]},mt}var ii;function ms(){return ii||(ii=1,(function(n){const t=fs();n.mul=function(s,e){const r=new Uint8Array(s.length+e.length-1);for(let o=0;o<s.length;o++)for(let l=0;l<e.length;l++)r[o+l]^=t.mul(s[o],e[l]);return r},n.mod=function(s,e){let r=new Uint8Array(s);for(;r.length-e.length>=0;){const o=r[0];for(let a=0;a<e.length;a++)r[a]^=t.mul(e[a],o);let l=0;for(;l<r.length&&r[l]===0;)l++;r=r.slice(l)}return r},n.generateECPolynomial=function(s){let e=new Uint8Array([1]);for(let r=0;r<s;r++)e=n.mul(e,new Uint8Array([1,t.exp(r)]));return e}})(de)),de}var he,si;function vs(){if(si)return he;si=1;const n=ms();function t(i){this.genPoly=void 0,this.degree=i,this.degree&&this.initialize(this.degree)}return t.prototype.initialize=function(s){this.degree=s,this.genPoly=n.generateECPolynomial(this.degree)},t.prototype.encode=function(s){if(!this.genPoly)throw new Error("Encoder not initialized");const e=new Uint8Array(s.length+this.degree);e.set(s);const r=n.mod(e,this.genPoly),o=this.degree-r.length;if(o>0){const l=new Uint8Array(this.degree);return l.set(r,o),l}return r},he=t,he}var pe={},ue={},ge={},ni;function Pi(){return ni||(ni=1,ge.isValid=function(t){return!isNaN(t)&&t>=1&&t<=40}),ge}var U={},ri;function Ti(){if(ri)return U;ri=1;const n="[0-9]+",t="[A-Z $%*+\\-./:]+";let i="(?:[u3000-u303F]|[u3040-u309F]|[u30A0-u30FF]|[uFF00-uFFEF]|[u4E00-u9FAF]|[u2605-u2606]|[u2190-u2195]|u203B|[u2010u2015u2018u2019u2025u2026u201Cu201Du2225u2260]|[u0391-u0451]|[u00A7u00A8u00B1u00B4u00D7u00F7])+";i=i.replace(/u/g,"\\u");const s="(?:(?![A-Z0-9 $%*+\\-./:]|"+i+`)(?:.|[\r
]))+`;U.KANJI=new RegExp(i,"g"),U.BYTE_KANJI=new RegExp("[^A-Z0-9 $%*+\\-./:]+","g"),U.BYTE=new RegExp(s,"g"),U.NUMERIC=new RegExp(n,"g"),U.ALPHANUMERIC=new RegExp(t,"g");const e=new RegExp("^"+i+"$"),r=new RegExp("^"+n+"$"),o=new RegExp("^[A-Z0-9 $%*+\\-./:]+$");return U.testKanji=function(a){return e.test(a)},U.testNumeric=function(a){return r.test(a)},U.testAlphanumeric=function(a){return o.test(a)},U}var oi;function et(){return oi||(oi=1,(function(n){const t=Pi(),i=Ti();n.NUMERIC={id:"Numeric",bit:1,ccBits:[10,12,14]},n.ALPHANUMERIC={id:"Alphanumeric",bit:2,ccBits:[9,11,13]},n.BYTE={id:"Byte",bit:4,ccBits:[8,16,16]},n.KANJI={id:"Kanji",bit:8,ccBits:[8,10,12]},n.MIXED={bit:-1},n.getCharCountIndicator=function(r,o){if(!r.ccBits)throw new Error("Invalid mode: "+r);if(!t.isValid(o))throw new Error("Invalid version: "+o);return o>=1&&o<10?r.ccBits[0]:o<27?r.ccBits[1]:r.ccBits[2]},n.getBestModeForData=function(r){return i.testNumeric(r)?n.NUMERIC:i.testAlphanumeric(r)?n.ALPHANUMERIC:i.testKanji(r)?n.KANJI:n.BYTE},n.toString=function(r){if(r&&r.id)return r.id;throw new Error("Invalid mode")},n.isValid=function(r){return r&&r.bit&&r.ccBits};function s(e){if(typeof e!="string")throw new Error("Param is not a string");switch(e.toLowerCase()){case"numeric":return n.NUMERIC;case"alphanumeric":return n.ALPHANUMERIC;case"kanji":return n.KANJI;case"byte":return n.BYTE;default:throw new Error("Unknown mode: "+e)}}n.from=function(r,o){if(n.isValid(r))return r;try{return s(r)}catch{return o}}})(ue)),ue}var ai;function bs(){return ai||(ai=1,(function(n){const t=tt(),i=ki(),s=Te(),e=et(),r=Pi(),o=7973,l=t.getBCHDigit(o);function a(p,u,v){for(let f=1;f<=40;f++)if(u<=n.getCapacity(f,v,p))return f}function d(p,u){return e.getCharCountIndicator(p,u)+4}function h(p,u){let v=0;return p.forEach(function(f){const I=d(f.mode,u);v+=I+f.getBitsLength()}),v}function c(p,u){for(let v=1;v<=40;v++)if(h(p,v)<=n.getCapacity(v,u,e.MIXED))return v}n.from=function(u,v){return r.isValid(u)?parseInt(u,10):v},n.getCapacity=function(u,v,f){if(!r.isValid(u))throw new Error("Invalid QR Code version");typeof f>"u"&&(f=e.BYTE);const I=t.getSymbolTotalCodewords(u),x=i.getTotalCodewordsCount(u,v),P=(I-x)*8;if(f===e.MIXED)return P;const C=P-d(f,u);switch(f){case e.NUMERIC:return Math.floor(C/10*3);case e.ALPHANUMERIC:return Math.floor(C/11*2);case e.KANJI:return Math.floor(C/13);case e.BYTE:default:return Math.floor(C/8)}},n.getBestVersionForData=function(u,v){let f;const I=s.from(v,s.M);if(Array.isArray(u)){if(u.length>1)return c(u,I);if(u.length===0)return 1;f=u[0]}else f=u;return a(f.mode,f.getLength(),I)},n.getEncodedBits=function(u){if(!r.isValid(u)||u<7)throw new Error("Invalid QR Code version");let v=u<<12;for(;t.getBCHDigit(v)-l>=0;)v^=o<<t.getBCHDigit(v)-l;return u<<12|v}})(pe)),pe}var fe={},li;function ys(){if(li)return fe;li=1;const n=tt(),t=1335,i=21522,s=n.getBCHDigit(t);return fe.getEncodedBits=function(r,o){const l=r.bit<<3|o;let a=l<<10;for(;n.getBCHDigit(a)-s>=0;)a^=t<<n.getBCHDigit(a)-s;return(l<<10|a)^i},fe}var me={},ve,ci;function _s(){if(ci)return ve;ci=1;const n=et();function t(i){this.mode=n.NUMERIC,this.data=i.toString()}return t.getBitsLength=function(s){return 10*Math.floor(s/3)+(s%3?s%3*3+1:0)},t.prototype.getLength=function(){return this.data.length},t.prototype.getBitsLength=function(){return t.getBitsLength(this.data.length)},t.prototype.write=function(s){let e,r,o;for(e=0;e+3<=this.data.length;e+=3)r=this.data.substr(e,3),o=parseInt(r,10),s.put(o,10);const l=this.data.length-e;l>0&&(r=this.data.substr(e),o=parseInt(r,10),s.put(o,l*3+1))},ve=t,ve}var be,di;function xs(){if(di)return be;di=1;const n=et(),t=["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"," ","$","%","*","+","-",".","/",":"];function i(s){this.mode=n.ALPHANUMERIC,this.data=s}return i.getBitsLength=function(e){return 11*Math.floor(e/2)+6*(e%2)},i.prototype.getLength=function(){return this.data.length},i.prototype.getBitsLength=function(){return i.getBitsLength(this.data.length)},i.prototype.write=function(e){let r;for(r=0;r+2<=this.data.length;r+=2){let o=t.indexOf(this.data[r])*45;o+=t.indexOf(this.data[r+1]),e.put(o,11)}this.data.length%2&&e.put(t.indexOf(this.data[r]),6)},be=i,be}var ye,hi;function ws(){if(hi)return ye;hi=1;const n=et();function t(i){this.mode=n.BYTE,typeof i=="string"?this.data=new TextEncoder().encode(i):this.data=new Uint8Array(i)}return t.getBitsLength=function(s){return s*8},t.prototype.getLength=function(){return this.data.length},t.prototype.getBitsLength=function(){return t.getBitsLength(this.data.length)},t.prototype.write=function(i){for(let s=0,e=this.data.length;s<e;s++)i.put(this.data[s],8)},ye=t,ye}var _e,pi;function Es(){if(pi)return _e;pi=1;const n=et(),t=tt();function i(s){this.mode=n.KANJI,this.data=s}return i.getBitsLength=function(e){return e*13},i.prototype.getLength=function(){return this.data.length},i.prototype.getBitsLength=function(){return i.getBitsLength(this.data.length)},i.prototype.write=function(s){let e;for(e=0;e<this.data.length;e++){let r=t.toSJIS(this.data[e]);if(r>=33088&&r<=40956)r-=33088;else if(r>=57408&&r<=60351)r-=49472;else throw new Error("Invalid SJIS character: "+this.data[e]+`
Make sure your charset is UTF-8`);r=(r>>>8&255)*192+(r&255),s.put(r,13)}},_e=i,_e}var xe={exports:{}},ui;function Ss(){return ui||(ui=1,(function(n){var t={single_source_shortest_paths:function(i,s,e){var r={},o={};o[s]=0;var l=t.PriorityQueue.make();l.push(s,0);for(var a,d,h,c,p,u,v,f,I;!l.empty();){a=l.pop(),d=a.value,c=a.cost,p=i[d]||{};for(h in p)p.hasOwnProperty(h)&&(u=p[h],v=c+u,f=o[h],I=typeof o[h]>"u",(I||f>v)&&(o[h]=v,l.push(h,v),r[h]=d))}if(typeof e<"u"&&typeof o[e]>"u"){var x=["Could not find a path from ",s," to ",e,"."].join("");throw new Error(x)}return r},extract_shortest_path_from_predecessor_list:function(i,s){for(var e=[],r=s;r;)e.push(r),i[r],r=i[r];return e.reverse(),e},find_path:function(i,s,e){var r=t.single_source_shortest_paths(i,s,e);return t.extract_shortest_path_from_predecessor_list(r,e)},PriorityQueue:{make:function(i){var s=t.PriorityQueue,e={},r;i=i||{};for(r in s)s.hasOwnProperty(r)&&(e[r]=s[r]);return e.queue=[],e.sorter=i.sorter||s.default_sorter,e},default_sorter:function(i,s){return i.cost-s.cost},push:function(i,s){var e={value:i,cost:s};this.queue.push(e),this.queue.sort(this.sorter)},pop:function(){return this.queue.shift()},empty:function(){return this.queue.length===0}}};n.exports=t})(xe)),xe.exports}var gi;function $s(){return gi||(gi=1,(function(n){const t=et(),i=_s(),s=xs(),e=ws(),r=Es(),o=Ti(),l=tt(),a=Ss();function d(x){return unescape(encodeURIComponent(x)).length}function h(x,P,C){const S=[];let z;for(;(z=x.exec(C))!==null;)S.push({data:z[0],index:z.index,mode:P,length:z[0].length});return S}function c(x){const P=h(o.NUMERIC,t.NUMERIC,x),C=h(o.ALPHANUMERIC,t.ALPHANUMERIC,x);let S,z;return l.isKanjiModeEnabled()?(S=h(o.BYTE,t.BYTE,x),z=h(o.KANJI,t.KANJI,x)):(S=h(o.BYTE_KANJI,t.BYTE,x),z=[]),P.concat(C,S,z).sort(function(_,m){return _.index-m.index}).map(function(_){return{data:_.data,mode:_.mode,length:_.length}})}function p(x,P){switch(P){case t.NUMERIC:return i.getBitsLength(x);case t.ALPHANUMERIC:return s.getBitsLength(x);case t.KANJI:return r.getBitsLength(x);case t.BYTE:return e.getBitsLength(x)}}function u(x){return x.reduce(function(P,C){const S=P.length-1>=0?P[P.length-1]:null;return S&&S.mode===C.mode?(P[P.length-1].data+=C.data,P):(P.push(C),P)},[])}function v(x){const P=[];for(let C=0;C<x.length;C++){const S=x[C];switch(S.mode){case t.NUMERIC:P.push([S,{data:S.data,mode:t.ALPHANUMERIC,length:S.length},{data:S.data,mode:t.BYTE,length:S.length}]);break;case t.ALPHANUMERIC:P.push([S,{data:S.data,mode:t.BYTE,length:S.length}]);break;case t.KANJI:P.push([S,{data:S.data,mode:t.BYTE,length:d(S.data)}]);break;case t.BYTE:P.push([{data:S.data,mode:t.BYTE,length:d(S.data)}])}}return P}function f(x,P){const C={},S={start:{}};let z=["start"];for(let y=0;y<x.length;y++){const _=x[y],m=[];for(let b=0;b<_.length;b++){const A=_[b],w=""+y+b;m.push(w),C[w]={node:A,lastCount:0},S[w]={};for(let $=0;$<z.length;$++){const E=z[$];C[E]&&C[E].node.mode===A.mode?(S[E][w]=p(C[E].lastCount+A.length,A.mode)-p(C[E].lastCount,A.mode),C[E].lastCount+=A.length):(C[E]&&(C[E].lastCount=A.length),S[E][w]=p(A.length,A.mode)+4+t.getCharCountIndicator(A.mode,P))}}z=m}for(let y=0;y<z.length;y++)S[z[y]].end=0;return{map:S,table:C}}function I(x,P){let C;const S=t.getBestModeForData(x);if(C=t.from(P,S),C!==t.BYTE&&C.bit<S.bit)throw new Error('"'+x+'" cannot be encoded with mode '+t.toString(C)+`.
 Suggested mode is: `+t.toString(S));switch(C===t.KANJI&&!l.isKanjiModeEnabled()&&(C=t.BYTE),C){case t.NUMERIC:return new i(x);case t.ALPHANUMERIC:return new s(x);case t.KANJI:return new r(x);case t.BYTE:return new e(x)}}n.fromArray=function(P){return P.reduce(function(C,S){return typeof S=="string"?C.push(I(S,null)):S.data&&C.push(I(S.data,S.mode)),C},[])},n.fromString=function(P,C){const S=c(P,l.isKanjiModeEnabled()),z=v(S),y=f(z,C),_=a.find_path(y.map,"start","end"),m=[];for(let b=1;b<_.length-1;b++)m.push(y.table[_[b]].node);return n.fromArray(u(m))},n.rawSplit=function(P){return n.fromArray(c(P,l.isKanjiModeEnabled()))}})(me)),me}var fi;function Cs(){if(fi)return se;fi=1;const n=tt(),t=Te(),i=ds(),s=hs(),e=ps(),r=us(),o=gs(),l=ki(),a=vs(),d=bs(),h=ys(),c=et(),p=$s();function u(y,_){const m=y.size,b=r.getPositions(_);for(let A=0;A<b.length;A++){const w=b[A][0],$=b[A][1];for(let E=-1;E<=7;E++)if(!(w+E<=-1||m<=w+E))for(let k=-1;k<=7;k++)$+k<=-1||m<=$+k||(E>=0&&E<=6&&(k===0||k===6)||k>=0&&k<=6&&(E===0||E===6)||E>=2&&E<=4&&k>=2&&k<=4?y.set(w+E,$+k,!0,!0):y.set(w+E,$+k,!1,!0))}}function v(y){const _=y.size;for(let m=8;m<_-8;m++){const b=m%2===0;y.set(m,6,b,!0),y.set(6,m,b,!0)}}function f(y,_){const m=e.getPositions(_);for(let b=0;b<m.length;b++){const A=m[b][0],w=m[b][1];for(let $=-2;$<=2;$++)for(let E=-2;E<=2;E++)$===-2||$===2||E===-2||E===2||$===0&&E===0?y.set(A+$,w+E,!0,!0):y.set(A+$,w+E,!1,!0)}}function I(y,_){const m=y.size,b=d.getEncodedBits(_);let A,w,$;for(let E=0;E<18;E++)A=Math.floor(E/3),w=E%3+m-8-3,$=(b>>E&1)===1,y.set(A,w,$,!0),y.set(w,A,$,!0)}function x(y,_,m){const b=y.size,A=h.getEncodedBits(_,m);let w,$;for(w=0;w<15;w++)$=(A>>w&1)===1,w<6?y.set(w,8,$,!0):w<8?y.set(w+1,8,$,!0):y.set(b-15+w,8,$,!0),w<8?y.set(8,b-w-1,$,!0):w<9?y.set(8,15-w-1+1,$,!0):y.set(8,15-w-1,$,!0);y.set(b-8,8,1,!0)}function P(y,_){const m=y.size;let b=-1,A=m-1,w=7,$=0;for(let E=m-1;E>0;E-=2)for(E===6&&E--;;){for(let k=0;k<2;k++)if(!y.isReserved(A,E-k)){let q=!1;$<_.length&&(q=(_[$]>>>w&1)===1),y.set(A,E-k,q),w--,w===-1&&($++,w=7)}if(A+=b,A<0||m<=A){A-=b,b=-b;break}}}function C(y,_,m){const b=new i;m.forEach(function(k){b.put(k.mode.bit,4),b.put(k.getLength(),c.getCharCountIndicator(k.mode,y)),k.write(b)});const A=n.getSymbolTotalCodewords(y),w=l.getTotalCodewordsCount(y,_),$=(A-w)*8;for(b.getLengthInBits()+4<=$&&b.put(0,4);b.getLengthInBits()%8!==0;)b.putBit(0);const E=($-b.getLengthInBits())/8;for(let k=0;k<E;k++)b.put(k%2?17:236,8);return S(b,y,_)}function S(y,_,m){const b=n.getSymbolTotalCodewords(_),A=l.getTotalCodewordsCount(_,m),w=b-A,$=l.getBlocksCount(_,m),E=b%$,k=$-E,q=Math.floor(b/$),gt=Math.floor(w/$),Ni=gt+1,Me=q-gt,Li=new a(Me);let Kt=0;const Pt=new Array($),Ie=new Array($);let Wt=0;const Fi=new Uint8Array(y.buffer);for(let it=0;it<$;it++){const Xt=it<k?gt:Ni;Pt[it]=Fi.slice(Kt,Kt+Xt),Ie[it]=Li.encode(Pt[it]),Kt+=Xt,Wt=Math.max(Wt,Xt)}const Gt=new Uint8Array(b);let Oe=0,j,H;for(j=0;j<Wt;j++)for(H=0;H<$;H++)j<Pt[H].length&&(Gt[Oe++]=Pt[H][j]);for(j=0;j<Me;j++)for(H=0;H<$;H++)Gt[Oe++]=Ie[H][j];return Gt}function z(y,_,m,b){let A;if(Array.isArray(y))A=p.fromArray(y);else if(typeof y=="string"){let q=_;if(!q){const gt=p.rawSplit(y);q=d.getBestVersionForData(gt,m)}A=p.fromString(y,q||40)}else throw new Error("Invalid data");const w=d.getBestVersionForData(A,m);if(!w)throw new Error("The amount of data is too big to be stored in a QR Code");if(!_)_=w;else if(_<w)throw new Error(`
The chosen QR Code version cannot contain this amount of data.
Minimum version required to store current data is: `+w+`.
`);const $=C(_,m,A),E=n.getSymbolSize(_),k=new s(E);return u(k,_),v(k),f(k,_),x(k,m,0),_>=7&&I(k,_),P(k,$),isNaN(b)&&(b=o.getBestMask(k,x.bind(null,k,m))),o.applyMask(b,k),x(k,m,b),{modules:k,version:_,errorCorrectionLevel:m,maskPattern:b,segments:A}}return se.create=function(_,m){if(typeof _>"u"||_==="")throw new Error("No input text");let b=t.M,A,w;return typeof m<"u"&&(b=t.from(m.errorCorrectionLevel,t.M),A=d.from(m.version),w=o.from(m.maskPattern),m.toSJISFunc&&n.setToSJISFunction(m.toSJISFunc)),z(_,A,b,w)},se}var we={},Ee={},mi;function Ri(){return mi||(mi=1,(function(n){function t(i){if(typeof i=="number"&&(i=i.toString()),typeof i!="string")throw new Error("Color should be defined as hex string");let s=i.slice().replace("#","").split("");if(s.length<3||s.length===5||s.length>8)throw new Error("Invalid hex color: "+i);(s.length===3||s.length===4)&&(s=Array.prototype.concat.apply([],s.map(function(r){return[r,r]}))),s.length===6&&s.push("F","F");const e=parseInt(s.join(""),16);return{r:e>>24&255,g:e>>16&255,b:e>>8&255,a:e&255,hex:"#"+s.slice(0,6).join("")}}n.getOptions=function(s){s||(s={}),s.color||(s.color={});const e=typeof s.margin>"u"||s.margin===null||s.margin<0?4:s.margin,r=s.width&&s.width>=21?s.width:void 0,o=s.scale||4;return{width:r,scale:r?4:o,margin:e,color:{dark:t(s.color.dark||"#000000ff"),light:t(s.color.light||"#ffffffff")},type:s.type,rendererOpts:s.rendererOpts||{}}},n.getScale=function(s,e){return e.width&&e.width>=s+e.margin*2?e.width/(s+e.margin*2):e.scale},n.getImageWidth=function(s,e){const r=n.getScale(s,e);return Math.floor((s+e.margin*2)*r)},n.qrToImageData=function(s,e,r){const o=e.modules.size,l=e.modules.data,a=n.getScale(o,r),d=Math.floor((o+r.margin*2)*a),h=r.margin*a,c=[r.color.light,r.color.dark];for(let p=0;p<d;p++)for(let u=0;u<d;u++){let v=(p*d+u)*4,f=r.color.light;if(p>=h&&u>=h&&p<d-h&&u<d-h){const I=Math.floor((p-h)/a),x=Math.floor((u-h)/a);f=c[l[I*o+x]?1:0]}s[v++]=f.r,s[v++]=f.g,s[v++]=f.b,s[v]=f.a}}})(Ee)),Ee}var vi;function As(){return vi||(vi=1,(function(n){const t=Ri();function i(e,r,o){e.clearRect(0,0,r.width,r.height),r.style||(r.style={}),r.height=o,r.width=o,r.style.height=o+"px",r.style.width=o+"px"}function s(){try{return document.createElement("canvas")}catch{throw new Error("You need to specify a canvas element")}}n.render=function(r,o,l){let a=l,d=o;typeof a>"u"&&(!o||!o.getContext)&&(a=o,o=void 0),o||(d=s()),a=t.getOptions(a);const h=t.getImageWidth(r.modules.size,a),c=d.getContext("2d"),p=c.createImageData(h,h);return t.qrToImageData(p.data,r,a),i(c,d,h),c.putImageData(p,0,0),d},n.renderToDataURL=function(r,o,l){let a=l;typeof a>"u"&&(!o||!o.getContext)&&(a=o,o=void 0),a||(a={});const d=n.render(r,o,a),h=a.type||"image/png",c=a.rendererOpts||{};return d.toDataURL(h,c.quality)}})(we)),we}var Se={},bi;function ks(){if(bi)return Se;bi=1;const n=Ri();function t(e,r){const o=e.a/255,l=r+'="'+e.hex+'"';return o<1?l+" "+r+'-opacity="'+o.toFixed(2).slice(1)+'"':l}function i(e,r,o){let l=e+r;return typeof o<"u"&&(l+=" "+o),l}function s(e,r,o){let l="",a=0,d=!1,h=0;for(let c=0;c<e.length;c++){const p=Math.floor(c%r),u=Math.floor(c/r);!p&&!d&&(d=!0),e[c]?(h++,c>0&&p>0&&e[c-1]||(l+=d?i("M",p+o,.5+u+o):i("m",a,0),a=0,d=!1),p+1<r&&e[c+1]||(l+=i("h",h),h=0)):a++}return l}return Se.render=function(r,o,l){const a=n.getOptions(o),d=r.modules.size,h=r.modules.data,c=d+a.margin*2,p=a.color.light.a?"<path "+t(a.color.light,"fill")+' d="M0 0h'+c+"v"+c+'H0z"/>':"",u="<path "+t(a.color.dark,"stroke")+' d="'+s(h,d,a.margin)+'"/>',v='viewBox="0 0 '+c+" "+c+'"',I='<svg xmlns="http://www.w3.org/2000/svg" '+(a.width?'width="'+a.width+'" height="'+a.width+'" ':"")+v+' shape-rendering="crispEdges">'+p+u+`</svg>
`;return typeof l=="function"&&l(null,I),I},Se}var yi;function Ps(){if(yi)return st;yi=1;const n=cs(),t=Cs(),i=As(),s=ks();function e(r,o,l,a,d){const h=[].slice.call(arguments,1),c=h.length,p=typeof h[c-1]=="function";if(!p&&!n())throw new Error("Callback required as last argument");if(p){if(c<2)throw new Error("Too few arguments provided");c===2?(d=l,l=o,o=a=void 0):c===3&&(o.getContext&&typeof d>"u"?(d=a,a=void 0):(d=a,a=l,l=o,o=void 0))}else{if(c<1)throw new Error("Too few arguments provided");return c===1?(l=o,o=a=void 0):c===2&&!o.getContext&&(a=l,l=o,o=void 0),new Promise(function(u,v){try{const f=t.create(l,a);u(r(f,o,a))}catch(f){v(f)}})}try{const u=t.create(l,a);d(null,r(u,o,a))}catch(u){d(u)}}return st.create=t.create,st.toCanvas=e.bind(null,i.render),st.toDataURL=e.bind(null,i.renderToDataURL),st.toString=e.bind(null,function(r,o,l){return s.render(r,l)}),st}var Ts=Ps();const Rs=ls(Ts);var Ms=Object.defineProperty,Is=Object.getOwnPropertyDescriptor,qt=(n,t,i,s)=>{for(var e=s>1?void 0:s?Is(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Ms(t,i,e),e};let ct=class extends D{constructor(){super(...arguments),this.variant="frosted",this.state="off",this.interactive=!1}render(){return g`
      <div
        class="card ${this.variant} ${this.interactive?"interactive":""}"
        data-state="${this.state}"
      >
        <div class="content">
          <slot></slot>
        </div>
      </div>
    `}};ct.styles=B`
    :host {
      display: block;
      box-sizing: border-box;
    }

    .card {
      border-radius: 20px;
      padding: 14px;
      transition: all 0.5s cubic-bezier(0.2, 0, 0, 1);
      position: relative;
      overflow: hidden;
      height: 100%;
      min-height: var(--glass-card-min-height, 150px);
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      border: 1px solid var(--t-card-border, rgba(255, 255, 255, 0.08));
      background: var(--t-card, rgba(255, 255, 255, 0.06));
      color: var(--t-text, #F0F2F5);
    }

    /* 变体 */
    .frosted {
      backdrop-filter: blur(32px) saturate(180%);
      -webkit-backdrop-filter: blur(32px) saturate(180%);
      box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.18),
        inset 0 1px 1px rgba(255, 255, 255, 0.08);
    }

    .clear {
      background: var(--t-card, rgba(255, 255, 255, 0.02));
      backdrop-filter: blur(16px) saturate(120%);
      -webkit-backdrop-filter: blur(16px) saturate(120%);
    }

    .elevated {
      background: var(--t-card-hover, rgba(255, 255, 255, 0.09));
      backdrop-filter: blur(48px) saturate(220%);
      -webkit-backdrop-filter: blur(48px) saturate(220%);
      box-shadow:
        0 24px 64px -8px rgba(0, 0, 0, 0.22),
        inset 0 1px 1px rgba(255, 255, 255, 0.12);
    }

    /* 开启状态：绿色辉光 */
    .card[data-state="on"] {
      background: var(--t-card-on, rgba(92, 219, 149, 0.12));
      border: 1.5px solid var(--t-card-on-border, rgba(92, 219, 149, 0.40));
      box-shadow:
        0 0 10px var(--t-card-on-glow, rgba(92, 219, 149, 0.20)),
        0 0 28px var(--t-card-on-glow, rgba(92, 219, 149, 0.12));
      animation: glow-pulse 4s ease-in-out infinite;
    }

    /* AI 控制状态：紫色辉光 */
    .card[data-state="ai-active"] {
      background: rgba(179, 136, 255, 0.14);
      border: 1.5px solid rgba(179, 136, 255, 0.45);
      box-shadow:
        0 0 12px rgba(179, 136, 255, 0.35),
        0 0 36px rgba(179, 136, 255, 0.18);
      animation: glow-pulse 3s ease-in-out infinite;
    }

    @keyframes glow-pulse {
      0%, 100% { filter: brightness(1); }
      50% { filter: brightness(1.15); }
    }

    .interactive:active {
      transform: scale(0.96) translateY(2px);
      transition-duration: 0.1s;
    }

    /* 顶部高亮折射线 */
    .card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      border-radius: inherit;
      padding: 1px;
      background: linear-gradient(135deg,
        rgba(255, 255, 255, 0.14) 0%,
        transparent 45%,
        transparent 55%,
        rgba(255, 255, 255, 0.05) 100%
      );
      -webkit-mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      pointer-events: none;
      z-index: 2;
    }

    .content {
      position: relative;
      z-index: 1;
      height: 100%;
      display: flex;
      flex-direction: column;
    }
  `;qt([T({type:String})],ct.prototype,"variant",2);qt([T({type:String})],ct.prototype,"state",2);qt([T({type:Boolean})],ct.prototype,"interactive",2);ct=qt([N("glass-card")],ct);var Os=Object.defineProperty,Ds=Object.getOwnPropertyDescriptor,Mi=(n,t,i,s)=>{for(var e=s>1?void 0:s?Ds(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Os(t,i,e),e};let Ot=class extends D{constructor(){super(...arguments),this.checked=!1}render(){return g`
      <div
        class="toggle"
        ?data-checked="${this.checked}"
        @click="${()=>{this.checked=!this.checked,this.dispatchEvent(new CustomEvent("change",{detail:this.checked}))}}"
      >
        <div class="thumb"></div>
      </div>
    `}};Ot.styles=B`
    :host {
      display: inline-block;
      vertical-align: middle;
    }

    .toggle {
      width: 52px;
      height: 28px;
      border-radius: 999px;
      background: var(--t-toggle-off, rgba(255, 255, 255, 0.08));
      border: 1px solid var(--t-toggle-off-border, rgba(255, 255, 255, 0.06));
      position: relative;
      cursor: pointer;
      transition: all 0.4s cubic-bezier(0.2, 0, 0, 1);
    }

    .toggle[data-checked] {
      background: rgba(92, 219, 149, 0.22);
      border-color: rgba(92, 219, 149, 0.42);
      box-shadow: 0 0 12px rgba(92, 219, 149, 0.18);
    }

    .thumb {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--t-text-hint, #9BA1B0);
      position: absolute;
      top: 3px;
      left: 3px;
      transition: all 0.4s cubic-bezier(0.2, 0, 0, 1);
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
    }

    .toggle[data-checked] .thumb {
      transform: translateX(24px);
      background: #fff;
      box-shadow: 0 0 10px rgba(255, 255, 255, 0.6);
    }
  `;Mi([T({type:Boolean})],Ot.prototype,"checked",2);Ot=Mi([N("glass-toggle")],Ot);var zs=Object.defineProperty,Bs=Object.getOwnPropertyDescriptor,Vt=(n,t,i,s)=>{for(var e=s>1?void 0:s?Bs(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&zs(t,i,e),e};let dt=class extends D{constructor(){super(...arguments),this.value=50,this.label="",this._isDragging=!1,this._handleMove=n=>{this._isDragging&&(n.cancelable&&n.preventDefault(),this._updateValue(n),this.dispatchEvent(new CustomEvent("input",{detail:this.value})))},this._handleEnd=()=>{this._isDragging&&(this._isDragging=!1,this.dispatchEvent(new CustomEvent("change",{detail:this.value}))),window.removeEventListener("mousemove",this._handleMove),window.removeEventListener("mouseup",this._handleEnd),window.removeEventListener("touchmove",this._handleMove),window.removeEventListener("touchend",this._handleEnd)}}render(){return g`
      <div class="container" @mousedown="${this._handleStart}" @touchstart="${this._handleStart}">
        <div class="track" id="track">
          <div class="fill" style="width: ${this.value}%"></div>
          <div class="thumb" style="left: ${this.value}%"></div>
        </div>
        <div class="value-display">${Math.round(this.value)}%</div>
      </div>
    `}_handleStart(n){this._isDragging=!0,this._updateValue(n);const t={passive:!1};window.addEventListener("mousemove",this._handleMove,t),window.addEventListener("mouseup",this._handleEnd,t),window.addEventListener("touchmove",this._handleMove,t),window.addEventListener("touchend",this._handleEnd,t)}_updateValue(n){const t=this.renderRoot.querySelector("#track");if(!t)return;const i=t.getBoundingClientRect(),s="touches"in n?n.touches[0].clientX:n.clientX,r=Math.max(0,Math.min(s-i.left,i.width))/i.width*100;this.value!==r&&(this.value=r)}};dt.styles=B`
    :host {
      display: block;
      width: 100%;
      user-select: none;
      margin: 8px 0;
    }

    .container {
      position: relative;
      height: 36px;
      display: flex;
      align-items: center;
      cursor: pointer;
    }

    .track {
      flex: 1;
      height: 10px;
      background: var(--t-track, rgba(255, 255, 255, 0.08));
      border-radius: 999px;
      position: relative;
      transition: background 0.3s;
    }

    .fill {
      height: 100%;
      background: linear-gradient(90deg,
        var(--glass-primary, #7AB8FF),
        color-mix(in srgb, var(--glass-primary, #7AB8FF) 70%, #fff)
      );
      border-radius: 999px;
      box-shadow: 0 0 8px var(--glass-primary-glow, rgba(122, 184, 255, 0.35));
      transition: box-shadow 0.3s;
    }

    .thumb {
      position: absolute;
      width: 22px;
      height: 22px;
      background: #fff;
      border-radius: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      box-shadow: 0 3px 10px rgba(0, 0, 0, 0.30);
      z-index: 2;
      transition: transform 0.1s, box-shadow 0.2s;
    }

    .container:active .thumb {
      transform: translate(-50%, -50%) scale(1.18);
      box-shadow: 0 0 0 4px var(--glass-primary-glow, rgba(122, 184, 255, 0.25)), 0 3px 10px rgba(0, 0, 0, 0.30);
    }

    .value-display {
      margin-left: 12px;
      font-size: 13px;
      font-weight: 800;
      color: var(--t-text-sec, rgba(240, 242, 245, 0.6));
      width: 36px;
      text-align: right;
      font-family: 'JetBrains Mono', 'Courier New', monospace;
    }
  `;Vt([T({type:Number})],dt.prototype,"value",2);Vt([T({type:String})],dt.prototype,"label",2);Vt([M()],dt.prototype,"_isDragging",2);dt=Vt([N("glass-slider")],dt);var Ns=Object.defineProperty,Ls=Object.getOwnPropertyDescriptor,Re=(n,t,i,s)=>{for(var e=s>1?void 0:s?Ls(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Ns(t,i,e),e};let wt=class extends D{constructor(){super(...arguments),this.rooms=[],this.activeRoom=""}render(){return g`
      <div class="nav-container">
        ${this.rooms.map(n=>g`
          <div
            class="nav-item"
            ?data-active="${this.activeRoom===n.id}"
            @click="${()=>this._selectRoom(n.id)}"
          >
            ${n.name}
          </div>
        `)}
      </div>
    `}_selectRoom(n){this.activeRoom=n,this.dispatchEvent(new CustomEvent("room-change",{detail:n}))}};wt.styles=B`
    :host {
      display: block;
      margin-bottom: 12px;
    }

    .nav-container {
      display: flex;
      gap: 10px;
      padding: 6px;
      overflow-x: auto;
      scrollbar-width: none;
    }

    .nav-container::-webkit-scrollbar {
      display: none;
    }

    .nav-item {
      padding: 9px 24px;
      border-radius: 999px;
      background: var(--t-nav-item, rgba(255, 255, 255, 0.03));
      border: 1px solid var(--t-nav-border, rgba(255, 255, 255, 0.05));
      color: var(--t-text-sec, rgba(240, 242, 245, 0.55));
      font-size: 14px;
      font-weight: 700;
      white-space: nowrap;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      position: relative;
      letter-spacing: 0.3px;
    }

    .nav-item:hover {
      background: var(--t-card-hover, rgba(255, 255, 255, 0.07));
      color: var(--t-text, #F0F2F5);
      transform: translateY(-1px);
    }

    .nav-item[data-active] {
      background: linear-gradient(135deg,
        color-mix(in srgb, var(--ai-purple, #B388FF) 18%, transparent),
        color-mix(in srgb, var(--glass-primary, #7AB8FF) 12%, transparent)
      );
      border-color: color-mix(in srgb, var(--ai-purple, #B388FF) 50%, transparent);
      color: var(--ai-purple, #B388FF);
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
      transform: scale(1.04);
    }

    .nav-item[data-active]::after {
      content: '';
      position: absolute;
      bottom: 5px;
      left: 38%;
      right: 38%;
      height: 2px;
      background: var(--ai-purple, #B388FF);
      box-shadow: 0 0 10px var(--ai-purple, #B388FF);
      border-radius: 4px;
    }
  `;Re([T({type:Array})],wt.prototype,"rooms",2);Re([T({type:String})],wt.prototype,"activeRoom",2);wt=Re([N("glass-nav")],wt);const ut=(n,t)=>{if(!n)return{light:"lightbulb",switch:"toggle_on",climate:"ac_unit",cover:"blinds",sensor:"sensors",binary_sensor:"sensors",scene:"scene",media_player:"play_circle",automation:"robot",fan:"fan"}[t||""]||"device_hub";const i=n.replace("mdi:","").replace(/-/g,"_"),s={white_balance_incandescent:"lightbulb",ceiling_light:"lightbulb",lamp:"lightbulb",wall_sconce:"lightbulb",floor_lamp:"lightbulb",led_strip:"lightbulb",weather_sunny:"sunny",weather_cloudy:"cloudy",weather_rainy:"rainy",weather_snowy:"snowy",thermometer:"thermostat",water_percent:"humidity_mid",motion_sensor:"motion_sensors",motion_sensor_off:"motion_sensors",shield_lock:"security",eye:"visibility",eye_outline:"visibility",eye_off:"visibility_off",eye_off_outline:"visibility_off",eye_circle:"visibility",eye_circle_outline:"visibility",cctv:"videocam",camera:"videocam",camera_outline:"videocam",camera_off:"videocam_off",video:"videocam",video_outline:"videocam",account:"person",account_outline:"person",account_multiple:"group",account_multiple_outline:"group",account_check:"how_to_reg",account_off:"person_off",run:"directions_run",walk:"directions_walk",human:"person",human_greeting:"waving_hand",window_shutter:"blinds",curtains:"blinds",door:"door_front",door_open:"door_open",door_closed:"door_front",air_conditioner:"ac_unit",television:"tv",speaker:"speaker",washing_machine:"local_laundry_service",dishwasher:"dishwasher_gen",fridge:"kitchen",coffee_maker:"coffee_maker",kettle:"kettle",microwave:"microwave",oven:"oven_gen",fan:"fan",robot_vacuum:"cleaning_services",power:"power_settings_new",power_plug:"electrical_services",power_plug_off:"electrical_services",flash:"bolt",wifi:"wifi",bluetooth:"bluetooth",home:"home",home_outline:"home",map_marker:"location_on",map_marker_outline:"location_on"},e=i.replace(/_outline$/,"").replace(/_filled$/,"");return s[i]||s[e]||e};var Fs=Object.defineProperty,Us=Object.getOwnPropertyDescriptor,F=(n,t,i,s)=>{for(var e=s>1?void 0:s?Us(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Fs(t,i,e),e};let Et=class extends D{constructor(){super(...arguments),this.device={},this.isAiControlled=!1,this._lpTimer=null,this._lpTriggered=!1,this._lpStartX=0,this._lpStartY=0}render(){var e;const n=this.device.state==="on",t=ut(this.device.icon,"light"),i=((e=this.device.attributes)==null?void 0:e.supported_color_modes)||[],s=i.length>0&&!(i.length===1&&i[0]==="onoff");return g`
      <glass-card
        ?state="${n?"on":"off"}"
        interactive
        @pointerdown="${this._onPointerDown}"
        @pointermove="${this._onPointerMove}"
        @pointerup="${this._onPointerUp}"
        @pointercancel="${this._onPointerCancel}"
        @contextmenu="${r=>r.preventDefault()}"
      >
        ${this.isAiControlled?g`<div class="ai-badge">AI</div>`:""}
        <div class="card-content">
          <div class="top-row">
            <div class="icon-box"
              style="color: ${n?"var(--glass-primary)":"inherit"}; background: ${n?"rgba(107, 170, 255, 0.1)":"rgba(255,255,255,0.05)"};"
            >
              <span>${t}</span>
            </div>
            <glass-toggle
              .checked="${n}"
              @change="${r=>{r.stopPropagation(),this._lpTriggered=!0,this._dispatchCall("light",r.detail?"turn_on":"turn_off")}}"
            ></glass-toggle>
          </div>

          <div class="bottom-info">
            <div class="name">${this.device.name}</div>
            <div class="info">${n?`${this.device.brightness||0}% 亮度`:"已关闭"}</div>
            ${s?g`<div class="hint">长按调光调色</div>`:""}
          </div>
        </div>
      </glass-card>
    `}_onPointerDown(n){n.button!==void 0&&n.button!==0||(this._lpTriggered=!1,this._lpStartX=n.clientX,this._lpStartY=n.clientY,this._lpTimer=setTimeout(()=>{var t;this._lpTriggered=!0,(t=navigator.vibrate)==null||t.call(navigator,40),this._showDetail()},600))}_onPointerMove(n){if(this._lpTimer===null)return;const t=n.clientX-this._lpStartX,i=n.clientY-this._lpStartY;Math.sqrt(t*t+i*i)>10&&(clearTimeout(this._lpTimer),this._lpTimer=null)}_onPointerUp(){this._lpTimer!==null&&(clearTimeout(this._lpTimer),this._lpTimer=null)}_onPointerCancel(){this._lpTimer!==null&&(clearTimeout(this._lpTimer),this._lpTimer=null)}_dispatchCall(n,t,i={}){this.dispatchEvent(new CustomEvent("service-call",{bubbles:!0,composed:!0,detail:{domain:n,service:t,data:{...i,entity_id:this.device.id}}}))}_showDetail(){this.dispatchEvent(new CustomEvent("show-detail",{bubbles:!0,composed:!0,detail:{entityId:this.device.id}}))}};Et.styles=B`
    :host { position: relative; display: block; height: 100%; }
    .ai-badge {
      position: absolute;
      top: 10px; left: 10px;
      background: var(--ai-purple, #B388FF);
      color: white;
      font-size: 7px;
      padding: 1px 4px;
      border-radius: 3px;
      z-index: 2;
      opacity: 0.85;
    }
    .card-content {
      display: flex;
      flex-direction: column;
      height: 100%;
      position: relative;
    }
    .top-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: auto;
    }
    .icon-box {
      width: 40px; height: 40px;
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      background: var(--t-input-bg, rgba(255,255,255,0.06));
      font-size: 24px;
      font-family: 'Material Symbols Outlined';
      transition: background 0.3s, color 0.3s;
    }
    .bottom-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
      margin-top: 8px;
    }
    .name { font-size: 13px; font-weight: 800; color: var(--t-text, #F0F2F5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .info { font-size: 10px; color: var(--t-text-sec, rgba(240,242,245,0.55)); font-weight: 600; }
    .hint { font-size: 9px; color: var(--t-text-hint, rgba(240,242,245,0.30)); margin-top: 2px; }
  `;F([T({type:Object})],Et.prototype,"device",2);F([T({type:Boolean})],Et.prototype,"isAiControlled",2);Et=F([N("light-card")],Et);let St=class extends D{constructor(){super(...arguments),this.device={},this.isAiControlled=!1}render(){const n=this.device.state!=="off",t=this.device.attributes.temperature||26,i=ut(this.device.icon,"climate");return g`
      <glass-card ?state="${n?"on":"off"}" interactive>
        ${this.isAiControlled?g`<div class="ai-badge">AI</div>`:""}
        <div class="card-content">
          <div class="top-row">
            <div class="icon-box" 
              style="color: ${n?"var(--glass-primary)":"inherit"};"
              @click="${this._showDetail}"
            >${i}</div>
            <glass-toggle 
              .checked="${n}"
              @change="${s=>this._dispatchCall("climate",(s.detail,"set_hvac_mode"),{hvac_mode:s.detail?"cool":"off"})}"
            ></glass-toggle>
          </div>
          
          <div class="bottom-info">
            <div class="name">${this.device.name}</div>
            <div class="state">${this.device.attributes.hvac_action||"空闲"}</div>
          </div>

          <div class="main-control">
            <div class="temp-display">
              <span class="temp-value">${t}</span>
              <span class="temp-unit">°C</span>
            </div>
            <div class="btn-group">
              <div class="btn" @click="${()=>this._adjustTemp(-.5)}">remove</div>
              <div class="btn" @click="${()=>this._adjustTemp(.5)}">add</div>
            </div>
          </div>
        </div>
      </glass-card>
    `}_adjustTemp(n){const t=this.device.attributes.temperature||26;this._dispatchCall("climate","set_temperature",{temperature:t+n})}_dispatchCall(n,t,i={}){this.dispatchEvent(new CustomEvent("service-call",{bubbles:!0,composed:!0,detail:{domain:n,service:t,data:{...i,entity_id:this.device.id}}}))}_showDetail(){this.dispatchEvent(new CustomEvent("show-detail",{bubbles:!0,composed:!0,detail:{entityId:this.device.id}}))}};St.styles=B`
    :host { position: relative; display: block; height: 100%; }
    .ai-badge {
      position: absolute;
      top: 8px; left: 8px;
      background: var(--glass-ai);
      color: white;
      font-size: 7px;
      padding: 1px 4px;
      border-radius: 3px;
      z-index: 2;
    }
    .card-content { display: flex; flex-direction: column; height: 100%; }
    .top-row { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: auto; }
    .icon-box {
      width: 40px; height: 40px; border-radius: 12px;
      background: rgba(255,255,255,0.05);
      display: flex; align-items: center; justify-content: center;
      font-family: 'Material Symbols Outlined'; font-size: 22px;
    }
    .main-control { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }
    .temp-display { display: flex; align-items: baseline; gap: 2px; }
    .temp-value { font-size: 28px; font-weight: 800; font-family: 'JetBrains Mono', monospace; color: #fff; }
    .temp-unit { font-size: 12px; opacity: 0.3; }
    .btn-group { display: flex; gap: 6px; }
    .btn {
      width: 36px; height: 36px; border-radius: 10px;
      background: rgba(255,255,255,0.05);
      display: flex; align-items: center; justify-content: center;
      font-family: 'Material Symbols Outlined'; font-size: 18px;
      cursor: pointer;
    }
    .bottom-info { margin-top: 8px; }
    .name { font-size: 13px; font-weight: 800; opacity: 0.9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .state { font-size: 10px; opacity: 0.4; font-weight: 600; }
  `;F([T({type:Object})],St.prototype,"device",2);F([T({type:Boolean})],St.prototype,"isAiControlled",2);St=F([N("climate-card")],St);let $t=class extends D{constructor(){super(...arguments),this.device={},this.isAiControlled=!1}render(){const n=this.device.attributes.current_position||0,t=n>0,i=ut(this.device.icon,"cover");return g`
      <glass-card ?state="${t?"on":"off"}" interactive>
        ${this.isAiControlled?g`<div class="ai-badge">AI</div>`:""}
        <div class="card-content">
          <div class="top-row">
            <div class="icon-box" style="color: ${t?"var(--glass-primary)":"inherit"}">${i}</div>
          </div>

          <div class="bottom-info">
            <div class="name">${this.device.name}</div>
            <div class="state">${t?`打开 ${n}%`:"已关闭"}</div>
          </div>

          <div class="controls">
            <glass-slider 
              style="--glass-card-min-height: 0px; margin: 2px 0;"
              .value="${n}"
              @change="${s=>this._dispatchCall("cover","set_cover_position",{position:s.detail})}"
            ></glass-slider>
            <div class="icon-btn-row">
              <div class="icon-btn" @click="${()=>this._dispatchCall("cover","open_cover")}">keyboard_arrow_up</div>
              <div class="icon-btn" @click="${()=>this._dispatchCall("cover","stop_cover")}">pause</div>
              <div class="icon-btn" @click="${()=>this._dispatchCall("cover","close_cover")}">keyboard_arrow_down</div>
            </div>
          </div>
        </div>
      </glass-card>
    `}_dispatchCall(n,t,i={}){this.dispatchEvent(new CustomEvent("service-call",{bubbles:!0,composed:!0,detail:{domain:n,service:t,data:{...i,entity_id:this.device.id}}}))}};$t.styles=B`
    :host { position: relative; display: block; height: 100%; }
    .ai-badge {
      position: absolute;
      top: 8px; left: 8px;
      background: var(--glass-ai);
      color: white;
      font-size: 7px;
      padding: 1px 4px;
      border-radius: 3px;
      z-index: 2;
    }
    .card-content { display: flex; flex-direction: column; height: 100%; }
    .top-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: auto; }
    .icon-box {
      width: 40px; height: 40px; border-radius: 12px;
      background: rgba(255,255,255,0.05);
      display: flex; align-items: center; justify-content: center;
      font-family: 'Material Symbols Outlined'; font-size: 22px;
    }
    .bottom-info { margin-top: 12px; }
    .name { font-size: 13px; font-weight: 800; opacity: 0.9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .state { font-size: 10px; opacity: 0.4; font-weight: 600; }
    .controls { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; }
    .icon-btn-row { display: flex; gap: 4px; }
    .icon-btn {
      font-family: 'Material Symbols Outlined';
      font-size: 16px;
      padding: 6px;
      border-radius: 8px;
      background: rgba(255,255,255,0.05);
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      flex: 1;
    }
  `;F([T({type:Object})],$t.prototype,"device",2);F([T({type:Boolean})],$t.prototype,"isAiControlled",2);$t=F([N("cover-card")],$t);let Dt=class extends D{constructor(){super(...arguments),this.device={}}render(){let n=this.device.state;const t=this.device.attributes||{},i=t.unit_of_measurement||"",s=t.device_class||"",e=ut(this.device.icon,"sensor"),r=c=>!c||/[\u4e00-\u9fa5]/.test(c)?c:c.replace(/\bPerson Occupancy\b/gi,"人员占用").replace(/\bPerson Count\b/gi,"人数").replace(/\bOccupancy\b/gi,"占用").replace(/\bMotion\b/gi,"移动检测").replace(/\bCam\s+[A-Fa-f0-9]+\b/gi,"摄像头").replace(/\bCamera\b/gi,"摄像头").replace(/\bZone\s+[A-Fa-f0-9]+\b/gi,"区域").trim().replace(/\s+/g," ");if(typeof n=="string"&&n.includes("T")&&n.includes(":"))try{const c=new Date(n);isNaN(c.getTime())||(n=`${(c.getMonth()+1).toString().padStart(2,"0")}-${c.getDate().toString().padStart(2,"0")} ${c.getHours().toString().padStart(2,"0")}:${c.getMinutes().toString().padStart(2,"0")}`)}catch{}const o=(c,p)=>{const u=c.toLowerCase();return u==="on"?p==="motion"||p==="occupancy"||p==="presence"?"有人":p==="door"||p==="window"||p==="opening"?"已打开":p==="moisture"?"漏水！":p==="smoke"?"烟雾！":p==="gas"?"燃气！":"开启":u==="off"?p==="motion"||p==="occupancy"||p==="presence"?"无人":p==="door"||p==="window"||p==="opening"?"已关闭":"正常":{playing:"播放中",paused:"已暂停",idle:"空闲",unavailable:"不可用",unknown:"未知",home:"在家",not_home:"离家",clear:"清空",detected:"检测到"}[u]||c},l=r(this.device.name),a=o(n,s),d=s===""&&/^\d+$/.test(String(n)),h=a.length>5?"18px":a.length>2?"22px":"28px";return g`
      <glass-card>
        <div class="sensor-box">
          <div class="icon-box">${e}</div>
          <div class="bottom-info">
            <div class="name">${l}</div>
            <div class="value-display">
              <span class="value" style="font-size: ${d?"28px":h}">
                ${d?n:a}
              </span>
              ${d?g`<span class="unit">人</span>`:g`<span class="unit">${i}</span>`}
            </div>
          </div>
        </div>
      </glass-card>
    `}};Dt.styles=B`
    :host { display: block; height: 100%; }
    .sensor-box {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .icon-box {
      width: 40px; height: 40px; border-radius: 12px;
      background: var(--t-input-bg, rgba(255,255,255,0.06));
      display: flex; align-items: center; justify-content: center;
      font-family: 'Material Symbols Outlined'; font-size: 22px;
      color: var(--glass-primary);
      margin-bottom: auto;
      transition: background 0.3s;
    }
    .bottom-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-top: 12px;
    }
    .value-display {
      display: flex;
      align-items: baseline;
      gap: 2px;
    }
    .value { font-size: 24px; font-weight: 600; font-family: 'HarmonyOS Sans SC', 'Inter', system-ui, sans-serif; color: var(--t-text, #F0F2F5); letter-spacing: -0.5px; }
    .unit { font-size: 12px; color: var(--t-text-hint, rgba(240,242,245,0.30)); font-weight: 600; }
    .name { font-size: 12px; font-weight: 800; color: var(--t-text-sec, rgba(240,242,245,0.55)); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  `;F([T({type:Object})],Dt.prototype,"device",2);Dt=F([N("sensor-card")],Dt);let Ct=class extends D{constructor(){super(...arguments),this.device={},this.isAiControlled=!1}render(){const n=this.device.state==="on"||this.device.state==="playing"||this.device.state==="open"||this.device.state==="active",t=this.device.id.split(".")[0],i=ut(this.device.icon,t),s=e=>{const r=e.toLowerCase();return{on:"已开启",off:"已关闭",playing:"播放中",paused:"已暂停",idle:"空闲",unavailable:"不可用",unknown:"未知",open:"已打开",closed:"已关闭"}[r]||e};return g`
      <glass-card ?state="${n?"on":"off"}" interactive @click="${this._toggle}">
        ${this.isAiControlled?g`<div class="ai-badge">AI</div>`:""}
        <div class="content">
          <div class="top-row">
            <div class="icon-box" style="color: ${n?"var(--glass-primary)":"inherit"}">
              ${i}
            </div>
            <glass-toggle .checked="${n}" @change="${this._toggle}"></glass-toggle>
          </div>
          <div class="bottom-info">
            <div class="name">${this.device.name}</div>
            <div class="state">${s(this.device.state)}</div>
          </div>
        </div>
      </glass-card>
    `}_toggle(n){n&&n.stopPropagation();const t=this.device.id.split(".")[0],i=this.device.state==="on"||this.device.state==="playing"||this.device.state==="open"||this.device.state==="active";let s=i?"turn_off":"turn_on";t==="cover"&&(s=i?"close_cover":"open_cover"),t==="media_player"&&(s=i?"media_stop":"media_play"),t==="vacuum"&&(s=i?"return_to_base":"start"),t==="scene"&&(s="turn_on"),this.dispatchEvent(new CustomEvent("service-call",{bubbles:!0,composed:!0,detail:{domain:t,service:s,data:{entity_id:this.device.id}}}))}};Ct.styles=B`
    :host { position: relative; display: block; height: 100%; }
    .ai-badge {
      position: absolute;
      top: 8px; left: 8px;
      background: var(--ai-purple, #B388FF);
      color: white;
      font-size: 7px;
      padding: 1px 4px;
      border-radius: 3px;
      z-index: 2;
    }
    .content {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .top-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: auto;
    }
    .icon-box {
      width: 40px; height: 40px; border-radius: 12px;
      background: var(--t-input-bg, rgba(255,255,255,0.06));
      display: flex; align-items: center; justify-content: center;
      font-family: 'Material Symbols Outlined'; font-size: 24px;
      transition: background 0.3s;
    }
    .bottom-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
      margin-top: 12px;
    }
    .name { font-size: 13px; font-weight: 800; color: var(--t-text, #F0F2F5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .state { font-size: 10px; color: var(--t-text-sec, rgba(240,242,245,0.55)); font-weight: 600; text-transform: uppercase; }
  `;F([T({type:Object})],Ct.prototype,"device",2);F([T({type:Boolean})],Ct.prototype,"isAiControlled",2);Ct=F([N("generic-device-card")],Ct);let ht=class extends D{constructor(){super(...arguments),this.scene={},this.isAiRecommended=!1,this.reason=""}render(){const n=ut(this.scene.icon,"scene");return g`
      <glass-card 
        interactive 
        style="--glass-card-min-height: 56px;"
        state="${this.isAiRecommended?"ai-active":"off"}"
        @click="${this._trigger}"
      >
        ${this.isAiRecommended?g`<div class="ai-badge">AI</div>`:""}
        <div class="scene-box">
          <span class="icon-main" style="color: ${this.isAiRecommended?"var(--glass-ai)":"var(--glass-on-surface)"}">${n}</span>
          <span class="scene-name">${this.scene.name}</span>
        </div>
      </glass-card>
    `}_trigger(){this.dispatchEvent(new CustomEvent("service-call",{bubbles:!0,composed:!0,detail:{domain:"scene",service:"turn_on",data:{entity_id:this.scene.id}}}))}};ht.styles=B`
    :host { display: block; position: relative; height: 100%; }
    .scene-box {
      height: 100%;
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 16px;
    }
    .icon-main {
      font-family: 'Material Symbols Outlined';
      font-size: 24px;
      opacity: 0.9;
    }
    .scene-name {
      font-size: 12px;
      font-weight: 800;
      opacity: 0.9;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
    }
    
    .ai-badge {
      position: absolute;
      top: 4px; right: 4px;
      font-size: 7px;
      padding: 1px 4px;
      background: var(--glass-ai);
      border-radius: 3px;
      color: white;
      text-transform: uppercase;
      z-index: 2;
    }
  `;F([T({type:Object})],ht.prototype,"scene",2);F([T({type:Boolean})],ht.prototype,"isAiRecommended",2);F([T({type:String})],ht.prototype,"reason",2);ht=F([N("scene-card")],ht);var js=Object.defineProperty,Hs=Object.getOwnPropertyDescriptor,Ii=(n,t,i,s)=>{for(var e=s>1?void 0:s?Hs(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&js(t,i,e),e};let zt=class extends D{constructor(){super(...arguments),this.aiState={status:"idle",lastAction:"",lastCorrection:"",recentAiActions:[],actionHistory:[]}}render(){const n=this.aiState.status==="thinking"||this.aiState.status==="推理中";return g`
      <div class="header">
        <div class="status-indicator">
          <div class="dot ${n?"active":""}"></div>
          <span>AI 领航员</span>
        </div>
      </div>

      ${this.aiState.lastCorrection?g`
        <div class="correction-banner">
          <span class="material-symbols-outlined correction-icon">edit_note</span>
          <div class="correction-content">
            ${this.aiState.lastCorrection}
          </div>
        </div>
      `:""}

      <div class="log-container">
        ${this.aiState.actionHistory.length>0?this.aiState.actionHistory.map(t=>g`
              <div class="log-item">${t}</div>
            `):g`
              <div class="empty-state">
                <span class="material-symbols-outlined" style="font-size: 40px;">Psychology</span>
                <span>等待指令中...</span>
              </div>
            `}
      </div>

      <div class="footer">
        系统状态: ${this.aiState.status}
      </div>
    `}};zt.styles=B`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      gap: 16px;
    }

    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 4px;
    }

    .correction-banner {
      background: rgba(255, 107, 107, 0.1);
      border: 1px solid rgba(255, 107, 107, 0.2);
      border-radius: 12px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 10px;
      animation: slideDown 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .correction-icon {
      color: #ff6b6b;
      font-size: 18px;
    }

    .correction-content {
      flex: 1;
      font-size: 10px;
      color: #ff6b6b;
      font-weight: 600;
      line-height: 1.4;
    }

    @keyframes slideDown {
      from { transform: translateY(-10px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 800;
      font-size: 14px;
      color: var(--glass-on-surface);
      letter-spacing: 0.5px;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: rgba(255,255,255,0.2);
      transition: all 0.5s ease;
    }

    .dot.active {
      background: var(--glass-ai);
      box-shadow: 0 0 20px var(--glass-ai), 0 0 40px rgba(179, 136, 255, 0.4);
      animation: pulse 1.5s infinite ease-in-out;
      position: relative;
    }

    .dot.active::after {
      content: '';
      position: absolute;
      top: -4px; left: -4px; right: -4px; bottom: -4px;
      border-radius: 50%;
      border: 2px solid var(--glass-ai);
      animation: ripple 1.5s infinite ease-out;
      opacity: 0;
    }

    @keyframes pulse {
      0%, 100% { transform: scale(1); filter: brightness(1); }
      50% { transform: scale(1.2); filter: brightness(1.5); }
    }

    @keyframes ripple {
      0% { transform: scale(1); opacity: 0.8; }
      100% { transform: scale(2.5); opacity: 0; }
    }

    .log-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 10px;
      overflow-y: auto;
      padding-right: 4px;
      scrollbar-width: none;
    }

    .log-container::-webkit-scrollbar {
      display: none;
    }

    .log-item {
      padding: 14px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.03);
      font-size: 10px; /* 进一步缩小字号 */
      line-height: 1.5;
      color: var(--glass-on-surface-secondary);
      animation: slideIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      position: relative;
      word-break: break-all; /* 强制换行防止溢出 */
      overflow-wrap: break-word;
    }

    .log-item:first-child {
      background: linear-gradient(135deg, rgba(179, 136, 255, 0.1) 0%, rgba(130, 177, 255, 0.05) 100%);
      border: 1px solid rgba(179, 136, 255, 0.2);
      color: var(--glass-on-surface);
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .log-item:first-child::before {
      content: 'LATEST';
      position: absolute;
      top: -6px; right: 12px;
      background: var(--glass-ai);
      color: white;
      font-size: 8px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 900;
      letter-spacing: 0.5px;
    }

    @keyframes slideIn {
      from { transform: translateX(-10px); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      opacity: 0.3;
      font-style: italic;
      gap: 8px;
    }

    .footer {
      font-size: 11px;
      opacity: 0.4;
      text-align: center;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
  `;Ii([T({type:Object})],zt.prototype,"aiState",2);zt=Ii([N("ai-status-panel")],zt);var qs=Object.defineProperty,Vs=Object.getOwnPropertyDescriptor,kt=(n,t,i,s)=>{for(var e=s>1?void 0:s?Vs(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&qs(t,i,e),e};let Z=class extends D{constructor(){super(...arguments),this.isRecording=!1,this.status="idle",this.text="点击开始语音指令",this.waveData=new Array(20).fill(0)}render(){return g`
      <div class="bar-content" @click="${this._handleClick}">
        <div class="wave-container">
          ${this.isRecording?this.waveData.map(n=>g`
              <div class="wave-bar" style="height:${Math.max(4,n*40)}px"></div>
            `):g`
              <div class="wave-bar static" style="animation-delay: 0s"></div>
              <div class="wave-bar static" style="animation-delay: -0.2s"></div>
              <div class="wave-bar static" style="animation-delay: -0.4s"></div>
              <div class="wave-bar static" style="animation-delay: -0.1s"></div>
            `}
        </div>

        <span class="voice-text ${this.isRecording?"recording":""}">
          ${this.text}
        </span>

        <div class="mic-button ${this.isRecording?"recording":""} ${this.status==="processing"?"processing":""}">
          <span class="icon">${this.isRecording?"stop":this.status==="processing"?"sync":"mic"}</span>
        </div>
      </div>
    `}_handleClick(){this.dispatchEvent(new CustomEvent("toggle-voice",{bubbles:!0,composed:!0}))}};Z.styles=B`
    :host {
      display: block;
      height: 100%;
      width: 100%;
      cursor: pointer;
    }

    .bar-content {
      display: flex;
      align-items: center;
      gap: 20px;
      height: 100%;
      padding: 0 24px;
    }

    .wave-container {
      display: flex;
      align-items: center;
      gap: 4px;
      min-width: 80px;
      height: 40px;
    }

    .wave-bar {
      width: 3px;
      background: var(--glass-info);
      border-radius: 3px;
      transition: height 0.1s ease-out;
    }

    .wave-bar.static {
      animation: wave 1s infinite alternate;
    }

    @keyframes wave {
      from { height: 8px; }
      to { height: 24px; }
    }

    .voice-text {
      font-size: 18px;
      font-weight: 500;
      color: var(--glass-on-surface);
      transition: opacity 0.3s;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .voice-text.recording {
      color: var(--glass-info);
    }

    .mic-button {
      margin-left: auto;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: var(--glass-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 15px var(--glass-primary-glow);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .mic-button.recording {
      background: var(--glass-error);
      box-shadow: 0 0 20px var(--glass-error-glow);
      transform: scale(1.1);
    }

    .mic-button.processing {
      background: var(--ai-purple);
      animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
      0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(179, 136, 255, 0.4); }
      70% { transform: scale(1.05); box-shadow: 0 0 0 15px rgba(179, 136, 255, 0); }
      100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(179, 136, 255, 0); }
    }

    .icon {
      font-family: 'Material Symbols Outlined';
      color: white;
      font-size: 24px;
    }
  `;kt([T({type:Boolean})],Z.prototype,"isRecording",2);kt([T({type:String})],Z.prototype,"status",2);kt([T({type:String})],Z.prototype,"text",2);kt([T({type:Array})],Z.prototype,"waveData",2);Z=kt([N("voice-bar")],Z);var Js=Object.defineProperty,Ys=Object.getOwnPropertyDescriptor,Oi=(n,t,i,s)=>{for(var e=s>1?void 0:s?Ys(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Js(t,i,e),e};let Bt=class extends D{constructor(){super(...arguments),this._time=new Date}connectedCallback(){super.connectedCallback(),this._timer=setInterval(()=>{this._time=new Date},1e3)}disconnectedCallback(){super.disconnectedCallback(),this._timer&&clearInterval(this._timer)}render(){const n=this._time.toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit",hour12:!1}),t=this._time.toLocaleDateString("zh-CN",{month:"long",day:"numeric"}),i=this._time.toLocaleDateString("zh-CN",{weekday:"long"});return g`
      <div class="time">${n}</div>
      <div class="info-box">
        <div class="date">${t}</div>
        <div class="weekday">${i}</div>
      </div>
    `}};Bt.styles=B`
    :host {
      display: flex;
      align-items: center;
      gap: 20px;
      padding: 12px 20px;
    }

    .time {
      font-size: 42px;
      font-weight: 900;
      font-family: 'JetBrains Mono', monospace;
      color: var(--glass-on-surface);
      line-height: 1;
      letter-spacing: -1.5px;
    }

    .info-box {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .date {
      font-size: 13px;
      color: var(--glass-on-surface-secondary);
      font-weight: 700;
      opacity: 0.9;
      white-space: nowrap;
    }

    .weekday {
      display: inline-block;
      padding: 2px 10px;
      background: rgba(179, 136, 255, 0.1);
      border: 1px solid rgba(179, 136, 255, 0.2);
      border-radius: 8px;
      font-size: 10px;
      color: #B388FF;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
      width: fit-content;
    }
  `;Oi([M()],Bt.prototype,"_time",2);Bt=Oi([N("clock-widget")],Bt);var Ks=Object.defineProperty,Ws=Object.getOwnPropertyDescriptor,Jt=(n,t,i,s)=>{for(var e=s>1?void 0:s?Ws(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Ks(t,i,e),e};let pt=class extends D{constructor(){super(...arguments),this.condition="晴",this.temperature=26,this.icon="wb_sunny"}render(){return g`
      <div class="icon">${this.icon}</div>
      <div class="info">
        <div class="temp">${this.temperature}°C</div>
        <div class="desc">${this.condition}</div>
      </div>
    `}};pt.styles=B`
    :host {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 12px;
    }

    .icon {
      font-family: 'Material Symbols Outlined';
      font-size: 32px;
      color: #FFD54F;
      filter: drop-shadow(0 0 8px rgba(255, 213, 79, 0.4));
    }

    .info {
      display: flex;
      flex-direction: column;
    }

    .temp {
      font-size: 20px;
      font-weight: 700;
      color: var(--glass-on-surface);
      line-height: 1;
    }

    .desc {
      font-size: 12px;
      color: var(--glass-on-surface-secondary);
      margin-top: 2px;
    }
  `;Jt([T({type:String})],pt.prototype,"condition",2);Jt([T({type:Number})],pt.prototype,"temperature",2);Jt([T({type:String})],pt.prototype,"icon",2);pt=Jt([N("weather-widget")],pt);var Gs=Object.defineProperty,Xs=Object.getOwnPropertyDescriptor,Di=(n,t,i,s)=>{for(var e=s>1?void 0:s?Xs(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Gs(t,i,e),e};let Nt=class extends D{constructor(){super(...arguments),this.stats=[]}render(){if(!this.stats||this.stats.length===0)return g`
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; opacity:0.3; gap:12px;">
          <span class="material-symbols-outlined" style="font-size:40px;">analytics</span>
          <span>暂无能耗数据</span>
        </div>
      `;const n=this.stats.slice(0,8),t=Math.max(...n.map(i=>i.on_minutes),1);return g`
      <div class="chart-container">
        ${n.map(i=>{const s=i.on_minutes/t*100,e=i.on_minutes>0?i.waste_minutes/i.on_minutes*100:0,r=i.entity_id.split(".").pop().replace(/_/g," ");return g`
            <div class="energy-row">
              <div class="row-header">
                <span class="device-name">${r}</span>
                <span class="time-val">${this._formatTime(i.on_minutes)} / 浪费 ${this._formatTime(i.waste_minutes)}</span>
              </div>
              <div class="progress-track">
                <div class="progress-on" style="width: ${s}%">
                  <div class="progress-waste" style="width: ${e}%"></div>
                </div>
              </div>
            </div>
          `})}
      </div>

      <div class="legend">
        <div class="legend-item">
          <div class="legend-dot" style="background: var(--glass-primary)"></div>
          <span>开启时长</span>
        </div>
        <div class="legend-item">
          <div class="legend-dot" style="background: var(--glass-error)"></div>
          <span>空房浪费</span>
        </div>
      </div>
    `}_formatTime(n){if(!n)return"0m";const t=Math.floor(n/60),i=Math.floor(n%60);return t>0?`${t}h${i}m`:`${i}m`}};Nt.styles=B`
    :host {
      display: block;
      height: 100%;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .chart-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto;
      scrollbar-width: none;
    }
    .chart-container::-webkit-scrollbar { display: none; }

    .energy-row {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .row-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
    }

    .device-name {
      font-weight: 500;
      color: var(--glass-on-surface);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 180px;
    }

    .time-val {
      font-size: 11px;
      opacity: 0.6;
      font-family: 'JetBrains Mono', monospace;
    }

    .progress-track {
      height: 8px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 4px;
      position: relative;
      overflow: hidden;
    }

    .progress-on {
      position: absolute;
      left: 0; top: 0; bottom: 0;
      background: var(--glass-primary);
      border-radius: 4px;
      transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 0 10px var(--glass-primary-glow);
    }

    .progress-waste {
      position: absolute;
      right: 0; top: 0; bottom: 0;
      background: var(--glass-error);
      opacity: 0.6;
      transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .legend {
      display: flex;
      gap: 16px;
      font-size: 11px;
      opacity: 0.5;
      padding-top: 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    .legend-item { display: flex; align-items: center; gap: 6px; }
    .legend-dot { width: 8px; height: 8px; border-radius: 50%; }
  `;Di([T({type:Array})],Nt.prototype,"stats",2);Nt=Di([N("energy-chart")],Nt);var Qs=Object.defineProperty,Zs=Object.getOwnPropertyDescriptor,zi=(n,t,i,s)=>{for(var e=s>1?void 0:s?Zs(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Qs(t,i,e),e};let Lt=class extends D{constructor(){super(...arguments),this.events=[]}render(){return!this.events||this.events.length===0?g`
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size: 32px;">videocam_off</span>
          <span>近期无视觉检测事件</span>
        </div>
      `:g`
      <div class="events-container">
        ${this.events.map((n,t)=>{var i;return g`
          <div class="event-card">
            <div class="thumbnail">
              ${n.thumbnail?g`<img src="${n.thumbnail}" alt="Snapshot">`:g`<span class="material-symbols-outlined" style="opacity: 0.3;">person</span>`}
            </div>
            <div class="event-info">
              <div class="camera-name">
                ${t===0?g`<span class="live-dot"></span>`:""}
                ${n.camera}
              </div>
              <div class="event-detail">
                ${n.type==="end"?"离开":"检测到"} ${n.label} ${(i=n.current_zones)!=null&&i.length?`@ ${n.current_zones.join(", ")}`:""}
              </div>
              <div class="score-badge">${Math.round(n.score*100)}% 置信度</div>
            </div>
          </div>
        `})}
      </div>
    `}};Lt.styles=B`
    :host {
      display: block;
      height: 100%;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .events-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 10px;
      overflow-y: auto;
      scrollbar-width: none;
    }
    .events-container::-webkit-scrollbar { display: none; }

    .event-card {
      background: rgba(255, 255, 255, 0.03);
      border-radius: 12px;
      padding: 10px;
      display: flex;
      gap: 12px;
      align-items: center;
      border: 1px solid rgba(255, 255, 255, 0.05);
      transition: all 0.3s ease;
      position: relative;
      overflow: hidden;
    }

    .event-card:first-child {
      background: rgba(179, 136, 255, 0.08);
      border: 1px solid rgba(179, 136, 255, 0.2);
      padding: 14px;
    }

    .event-card:first-child::after {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, var(--ai-purple), transparent);
      animation: scan 2s linear infinite;
    }

    @keyframes scan {
      0% { transform: translateY(0); opacity: 0; }
      50% { opacity: 1; }
      100% { transform: translateY(80px); opacity: 0; }
    }

    .live-dot {
      width: 6px;
      height: 6px;
      background: #ff5252;
      border-radius: 50%;
      margin-right: 6px;
      display: inline-block;
      box-shadow: 0 0 10px #ff5252;
      animation: blink 1s infinite;
    }

    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }

    .event-card:hover {
      background: rgba(255, 255, 255, 0.06);
    }

    .thumbnail {
      width: 64px;
      height: 64px;
      border-radius: 8px;
      background: rgba(0, 0, 0, 0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      flex-shrink: 0;
    }

    .thumbnail img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .event-info {
      flex: 1;
      min-width: 0;
    }

    .camera-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--glass-on-surface);
      margin-bottom: 2px;
    }

    .event-detail {
      font-size: 11px;
      opacity: 0.6;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .score-badge {
      font-size: 10px;
      background: var(--glass-primary);
      color: white;
      padding: 2px 6px;
      border-radius: 4px;
      margin-top: 4px;
      display: inline-block;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      opacity: 0.3;
      gap: 8px;
      font-size: 13px;
    }
  `;zi([T({type:Array})],Lt.prototype,"events",2);Lt=zi([N("frigate-events-panel")],Lt);var tn=Object.defineProperty,en=Object.getOwnPropertyDescriptor,Yt=(n,t,i,s)=>{for(var e=s>1?void 0:s?en(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&tn(t,i,e),e};let Ft=class extends D{constructor(){super(...arguments),this.device={}}render(){const n=this.device.attributes||{},t=this.device.brightness!==void 0?this.device.brightness:n.brightness?Math.round(n.brightness/255*100):0,i=n.color_temp_kelvin||(n.color_temp?Math.round(1e6/n.color_temp):null),s=n.min_color_temp_kelvin||(n.max_mireds?Math.round(1e6/n.max_mireds):2700),e=n.max_color_temp_kelvin||(n.min_mireds?Math.round(1e6/n.min_mireds):6500),r=i??Math.round((s+e)/2),o=Math.min(100,Math.max(0,Math.round((r-s)/(e-s)*100))),l=n.supported_color_modes||[],a=l.includes("color_temp"),d=l.some(c=>["hs","rgb","xy","rgbw","rgbww"].includes(c)),h=[{name:"暖光",color:"#FFB347",k:2700},{name:"自然",color:"#FFE0B2",k:3500},{name:"阅读",color:"#FFF5DC",k:4e3},{name:"冷白",color:"#E8F4FD",k:5e3},{name:"日光",color:"#E3F2FD",k:6e3}].filter(c=>c.k>=s&&c.k<=e);return g`
      <div class="container">
        <!-- 亮度调节 -->
        <div class="section">
          <div class="value-display">
            <div class="label">亮度调节</div>
            <div class="value">${t}<span class="unit">%</span></div>
          </div>
          <glass-slider
            .value="${t}"
            @change="${c=>this._call("turn_on",{brightness_pct:c.detail})}"
          ></glass-slider>
        </div>

        <!-- 色温调节（仅支持色温的灯显示） -->
        ${a?g`
          <div class="section">
            <div class="value-display">
              <div class="label">色温调节</div>
              <div class="value">${r}<span class="unit">K</span></div>
            </div>
            <glass-slider
              style="--glass-primary: #ffb347; --glass-primary-glow: rgba(255,179,71,0.3);"
              .value="${o}"
              @change="${c=>{const p=Math.round(s+c.detail/100*(e-s));this._call("turn_on",{color_temp_kelvin:p})}}"
            ></glass-slider>
            <!-- 色温预设快捷按钮 -->
            ${h.length>0?g`
              <div class="color-presets">
                ${h.map(c=>g`
                  <div
                    class="color-dot ${r===c.k?"active":""}"
                    style="background: ${c.color}; color: ${c.color};"
                    title="${c.name} ${c.k}K"
                    @click="${()=>this._call("turn_on",{color_temp_kelvin:c.k})}"
                  ></div>
                `)}
              </div>
            `:""}
          </div>
        `:""}

        <!-- RGB 颜色预设（仅支持彩色的灯显示） -->
        ${d?g`
          <div class="section">
            <div class="label">颜色预设</div>
            <div class="color-presets">
              ${[{color:"#FF8A80",rgb:[255,138,128]},{color:"#B388FF",rgb:[179,136,255]},{color:"#80D8FF",rgb:[128,216,255]},{color:"#CCFF90",rgb:[204,255,144]},{color:"#FFD180",rgb:[255,209,128]}].map(c=>g`
                <div
                  class="color-dot"
                  style="background: ${c.color}; color: ${c.color};"
                  @click="${()=>this._call("turn_on",{rgb_color:c.rgb})}"
                ></div>
              `)}
            </div>
          </div>
        `:""}
      </div>
    `}_call(n,t){this.dispatchEvent(new CustomEvent("service-call",{bubbles:!0,composed:!0,detail:{domain:"light",service:n,data:{...t,entity_id:this.device.id}}}))}};Ft.styles=B`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      color: var(--t-text, #F0F2F5);
    }

    .container {
      display: flex;
      flex-direction: column;
      gap: 32px;
      padding: 20px;
    }

    .section {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .label {
      font-size: 14px;
      font-weight: 700;
      color: var(--t-text-sec, rgba(240, 242, 245, 0.55));
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .value-display {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }

    .value {
      font-size: 32px;
      font-weight: 900;
      font-family: 'JetBrains Mono', monospace;
      color: var(--t-text, #F0F2F5);
    }

    .unit {
      font-size: 16px;
      color: var(--t-text-hint, rgba(240, 242, 245, 0.30));
      margin-left: 4px;
    }

    .color-presets {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
    }

    .color-dot {
      aspect-ratio: 1;
      border-radius: 50%;
      cursor: pointer;
      border: 3px solid var(--t-card-border, rgba(255, 255, 255, 0.10));
      transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .color-dot:active {
      transform: scale(0.85);
    }

    .color-dot.active {
      border-color: var(--t-text, white);
      box-shadow: 0 0 20px currentColor;
    }
  `;Yt([T({type:Object})],Ft.prototype,"device",2);Ft=Yt([N("light-detail-panel")],Ft);let Ut=class extends D{constructor(){super(...arguments),this.device={}}render(){const n=this.device.state,t=this.device.attributes.fan_mode||"auto";return g`
      <div class="container">
        <div class="section">
          <div class="label">运行模式</div>
          <div class="mode-grid">
            ${[{id:"cool",name:"制冷",icon:"ac_unit"},{id:"heat",name:"制热",icon:"wb_sunny"},{id:"dry",name:"除湿",icon:"water_drop"},{id:"fan_only",name:"送风",icon:"air"},{id:"off",name:"关闭",icon:"power_settings_new"}].map(s=>g`
              <div class="mode-btn ${n===s.id?"active":""}" @click="${()=>this._call("set_hvac_mode",{hvac_mode:s.id})}">
                <span class="icon-main material-symbols-outlined">${s.icon}</span>
                <span class="mode-name">${s.name}</span>
              </div>
            `)}
          </div>
        </div>

        <div class="section">
          <div class="label">风速调节</div>
          <div class="fan-row">
            ${["low","medium","high","auto"].map(s=>g`
              <div class="fan-btn ${t===s?"active":""}" @click="${()=>this._call("set_fan_mode",{fan_mode:s})}">
                ${s==="low"?"低":s==="medium"?"中":s==="high"?"高":"自动"}
              </div>
            `)}
          </div>
        </div>

        <div class="section">
          <div class="label">定时关闭</div>
          <div style="display:flex; gap:12px;">
            ${[30,60,120].map(s=>g`
              <div class="fan-btn" style="flex:1;">${s}分钟</div>
            `)}
          </div>
        </div>
      </div>
    `}_call(n,t){this.dispatchEvent(new CustomEvent("service-call",{bubbles:!0,composed:!0,detail:{domain:"climate",service:n,data:{...t,entity_id:this.device.id}}}))}};Ut.styles=B`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      color: white;
    }

    .container {
      display: flex;
      flex-direction: column;
      gap: 32px;
      padding: 20px;
    }

    .section {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .label {
      font-size: 14px;
      font-weight: 700;
      opacity: 0.5;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .mode-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
    }

    .mode-btn {
      padding: 16px 8px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      transition: all 0.3s;
    }

    .mode-btn .icon-main { font-size: 24px; opacity: 0.6; }
    .mode-btn .mode-name { font-size: 11px; font-weight: 700; opacity: 0.4; }

    .mode-btn.active {
      background: rgba(0, 229, 255, 0.1);
      border-color: var(--ai-cyan);
    }
    .mode-btn.active .icon-main { opacity: 1; color: var(--ai-cyan); }
    .mode-btn.active .mode-name { opacity: 1; color: var(--ai-cyan); }

    .fan-row {
      display: flex;
      gap: 12px;
    }

    .fan-btn {
      flex: 1;
      padding: 14px;
      background: rgba(255,255,255,0.05);
      border-radius: 12px;
      text-align: center;
      font-size: 13px;
      font-weight: 700;
      opacity: 0.6;
      cursor: pointer;
    }

    .fan-btn.active {
      background: var(--ai-purple);
      opacity: 1;
      box-shadow: 0 4px 12px rgba(179, 136, 255, 0.3);
    }
  `;Yt([T({type:Object})],Ut.prototype,"device",2);Ut=Yt([N("climate-detail-panel")],Ut);const sn=1,jt=2,$e=3,nn=4,rn=5;function on(n){return{type:"auth",access_token:n}}function an(){return{type:"supported_features",id:1,features:{coalesce_messages:1}}}function ln(){return{type:"get_states"}}function cn(){return{type:"auth/current_user"}}function dn(n,t,i,s,e){const r={type:"call_service",domain:n,service:t,target:s,return_response:e};return i&&(r.service_data=i),r}function hn(n){const t={type:"subscribe_events"};return n&&(t.event_type=n),t}function _i(n){return{type:"unsubscribe_events",subscription:n}}function pn(){return{type:"ping"}}function un(n,t){return{type:"result",success:!1,error:{code:n,message:t}}}const Bi=(n,t,i,s)=>{const[e,r,o]=n.split(".",3);return Number(e)>t||Number(e)===t&&(s===void 0?Number(r)>=i:Number(r)>i)||s!==void 0&&Number(e)===t&&Number(r)===i&&Number(o)>=s},gn="auth_invalid",fn="auth_ok";function mn(n){if(!n.auth)throw nn;const t=n.auth;let i=t.expired?t.refreshAccessToken().then(()=>{i=void 0},()=>{i=void 0}):void 0;const s=t.wsUrl;function e(r,o,l){const a=new WebSocket(s);let d=!1;const h=()=>{if(a.removeEventListener("close",h),d){l(jt);return}if(r===0){l(sn);return}const u=r===-1?-1:r-1;setTimeout(()=>e(u,o,l),1e3)},c=async u=>{try{t.expired&&await(i||t.refreshAccessToken()),a.send(JSON.stringify(on(t.accessToken)))}catch(v){d=v===jt,a.close()}},p=async u=>{const v=JSON.parse(u.data);switch(v.type){case gn:d=!0,a.close();break;case fn:a.removeEventListener("open",c),a.removeEventListener("message",p),a.removeEventListener("close",h),a.removeEventListener("error",h),a.haVersion=v.ha_version,Bi(a.haVersion,2022,9)&&a.send(JSON.stringify(an())),o(a);break}};a.addEventListener("open",c),a.addEventListener("message",p),a.addEventListener("close",h),a.addEventListener("error",h)}return new Promise((r,o)=>e(n.setupRetry,r,o))}class vn{constructor(t,i){this._handleMessage=s=>{let e=JSON.parse(s.data);Array.isArray(e)||(e=[e]),e.forEach(r=>{const o=this.commands.get(r.id);switch(r.type){case"event":o?o.callback(r.event):(console.warn(`Received event for unknown subscription ${r.id}. Unsubscribing.`),this.sendMessagePromise(_i(r.id)).catch(l=>{}));break;case"result":o&&(r.success?(o.resolve(r.result),"subscribe"in o||this.commands.delete(r.id)):(o.reject(r.error),this.commands.delete(r.id)));break;case"pong":o?(o.resolve(),this.commands.delete(r.id)):console.warn(`Received unknown pong response ${r.id}`);break}})},this._handleClose=async()=>{const s=this.commands;if(this.commandId=1,this.oldSubscriptions=this.commands,this.commands=new Map,this.socket=void 0,s.forEach(o=>{"subscribe"in o||o.reject(un($e,"Connection lost"))}),this.closeRequested)return;this.fireEvent("disconnected");const e=Object.assign(Object.assign({},this.options),{setupRetry:0}),r=o=>{setTimeout(async()=>{if(!this.closeRequested)try{const l=await e.createSocket(e);this._setSocket(l)}catch(l){if(this._queuedMessages){const a=this._queuedMessages;this._queuedMessages=void 0;for(const d of a)d.reject&&d.reject($e)}l===jt?this.fireEvent("reconnect-error",l):r(o+1)}},Math.min(o,5)*1e3)};this.suspendReconnectPromise&&(await this.suspendReconnectPromise,this.suspendReconnectPromise=void 0,this._queuedMessages=[]),r(0)},this.options=i,this.commandId=2,this.commands=new Map,this.eventListeners=new Map,this.closeRequested=!1,this._setSocket(t)}get connected(){return this.socket!==void 0&&this.socket.readyState==this.socket.OPEN}_setSocket(t){this.socket=t,this.haVersion=t.haVersion,t.addEventListener("message",this._handleMessage),t.addEventListener("close",this._handleClose);const i=this.oldSubscriptions;i&&(this.oldSubscriptions=void 0,i.forEach(e=>{"subscribe"in e&&e.subscribe&&e.subscribe().then(r=>{e.unsubscribe=r,e.resolve()})}));const s=this._queuedMessages;if(s){this._queuedMessages=void 0;for(const e of s)e.resolve()}this.fireEvent("ready")}addEventListener(t,i){let s=this.eventListeners.get(t);s||(s=[],this.eventListeners.set(t,s)),s.push(i)}removeEventListener(t,i){const s=this.eventListeners.get(t);if(!s)return;const e=s.indexOf(i);e!==-1&&s.splice(e,1)}fireEvent(t,i){(this.eventListeners.get(t)||[]).forEach(s=>s(this,i))}suspendReconnectUntil(t){this.suspendReconnectPromise=t}suspend(){if(!this.suspendReconnectPromise)throw new Error("Suspend promise not set");this.socket&&this.socket.close()}reconnect(t=!1){if(this.socket){if(!t){this.socket.close();return}this.socket.removeEventListener("message",this._handleMessage),this.socket.removeEventListener("close",this._handleClose),this.socket.close(),this._handleClose()}}close(){this.closeRequested=!0,this.socket&&this.socket.close()}async subscribeEvents(t,i){return this.subscribeMessage(t,hn(i))}ping(){return this.sendMessagePromise(pn())}sendMessage(t,i){if(!this.connected)throw $e;if(this._queuedMessages){if(i)throw new Error("Cannot queue with commandId");this._queuedMessages.push({resolve:()=>this.sendMessage(t)});return}i||(i=this._genCmdId()),t.id=i,this.socket.send(JSON.stringify(t))}sendMessagePromise(t){return new Promise((i,s)=>{if(this._queuedMessages){this._queuedMessages.push({reject:s,resolve:async()=>{try{i(await this.sendMessagePromise(t))}catch(r){s(r)}}});return}const e=this._genCmdId();this.commands.set(e,{resolve:i,reject:s}),this.sendMessage(t,e)})}async subscribeMessage(t,i,s){if(this._queuedMessages&&await new Promise((r,o)=>{this._queuedMessages.push({resolve:r,reject:o})}),s!=null&&s.preCheck&&!await s.preCheck())throw new Error("Pre-check failed");let e;return await new Promise((r,o)=>{const l=this._genCmdId();e={resolve:r,reject:o,callback:t,subscribe:(s==null?void 0:s.resubscribe)!==!1?()=>this.subscribeMessage(t,i,s):void 0,unsubscribe:async()=>{this.connected&&await this.sendMessagePromise(_i(l)),this.commands.delete(l)}},this.commands.set(l,e);try{this.sendMessage(i,l)}catch{}}),()=>e.unsubscribe()}_genCmdId(){return++this.commandId}}const bn=n=>n*1e3+Date.now();async function yn(n,t,i){const s=typeof location<"u"&&location;if(s&&s.protocol==="https:"){const l=document.createElement("a");if(l.href=n,l.protocol==="http:"&&l.hostname!=="localhost")throw rn}const e=new FormData;t!==null&&e.append("client_id",t),Object.keys(i).forEach(l=>{e.append(l,i[l])});const r=await fetch(`${n}/auth/token`,{method:"POST",credentials:"same-origin",body:e});if(!r.ok)throw r.status===400||r.status===403?jt:new Error("Unable to fetch tokens");const o=await r.json();return o.hassUrl=n,o.clientId=t,o.expires=bn(o.expires_in),o}class _n{constructor(t,i){this.data=t,this._saveTokens=i}get wsUrl(){return`ws${this.data.hassUrl.substr(4)}/api/websocket`}get accessToken(){return this.data.access_token}get expired(){return Date.now()>this.data.expires}async refreshAccessToken(){if(!this.data.refresh_token)throw new Error("No refresh_token");const t=await yn(this.data.hassUrl,this.data.clientId,{grant_type:"refresh_token",refresh_token:this.data.refresh_token});t.refresh_token=this.data.refresh_token,this.data=t,this._saveTokens&&this._saveTokens(t)}async revoke(){if(!this.data.refresh_token)throw new Error("No refresh_token to revoke");const t=new FormData;t.append("token",this.data.refresh_token),await fetch(`${this.data.hassUrl}/auth/revoke`,{method:"POST",credentials:"same-origin",body:t}),this._saveTokens&&this._saveTokens(null)}}function xn(n,t){return new _n({hassUrl:n,clientId:null,expires:Date.now()+1e11,refresh_token:"",access_token:t,expires_in:1e11})}const wn=n=>{let t=[];function i(e){let r=[];for(let o=0;o<t.length;o++)t[o]===e?e=null:r.push(t[o]);t=r}function s(e,r){n=r?e:Object.assign(Object.assign({},n),e);let o=t;for(let l=0;l<o.length;l++)o[l](n)}return{get state(){return n},action(e){function r(o){s(o,!1)}return function(){let o=[n];for(let a=0;a<arguments.length;a++)o.push(arguments[a]);let l=e.apply(this,o);if(l!=null)return l instanceof Promise?l.then(r):r(l)}},setState:s,clearState(){n=void 0},subscribe(e){return t.push(e),()=>{i(e)}}}},En=5e3,xi=(n,t,i,s,e={unsubGrace:!0})=>{if(n[t])return n[t];let r=0,o,l,a=wn();const d=()=>{if(!i)throw new Error("Collection does not support refresh");return i(n).then(f=>a.setState(f,!0))},h=()=>d().catch(f=>{if(n.connected)throw f}),c=()=>{if(l!==void 0){clearTimeout(l),l=void 0;return}s&&(o=s(n,a)),i&&(n.addEventListener("ready",h),h()),n.addEventListener("disconnected",v)},p=()=>{l=void 0,o&&o.then(f=>{f()}),a.clearState(),n.removeEventListener("ready",d),n.removeEventListener("disconnected",v)},u=()=>{l=setTimeout(p,En)},v=()=>{l&&(clearTimeout(l),p())};return n[t]={get state(){return a.state},refresh:d,subscribe(f){r++,r===1&&c();const I=a.subscribe(f);return a.state!==void 0&&setTimeout(()=>f(a.state),0),()=>{I(),r--,r||(e.unsubGrace?u():p())}}},n[t]},Sn=n=>n.sendMessagePromise(ln()),$n=n=>n.sendMessagePromise(cn()),Cn=(n,t,i,s,e,r)=>n.sendMessagePromise(dn(t,i,s,e,r));function An(n,t){const i=Object.assign({},n.state);if(t.a)for(const s in t.a){const e=t.a[s];let r=new Date(e.lc*1e3).toISOString();i[s]={entity_id:s,state:e.s,attributes:e.a,context:typeof e.c=="string"?{id:e.c,parent_id:null,user_id:null}:e.c,last_changed:r,last_updated:e.lu?new Date(e.lu*1e3).toISOString():r}}if(t.r)for(const s of t.r)delete i[s];if(t.c)for(const s in t.c){let e=i[s];if(!e){console.warn("Received state update for unknown entity",s);continue}e=Object.assign({},e);const{"+":r,"-":o}=t.c[s],l=(r==null?void 0:r.a)||(o==null?void 0:o.a),a=l?Object.assign({},e.attributes):e.attributes;if(r&&(r.s!==void 0&&(e.state=r.s),r.c&&(typeof r.c=="string"?e.context=Object.assign(Object.assign({},e.context),{id:r.c}):e.context=Object.assign(Object.assign({},e.context),r.c)),r.lc?e.last_updated=e.last_changed=new Date(r.lc*1e3).toISOString():r.lu&&(e.last_updated=new Date(r.lu*1e3).toISOString()),r.a&&Object.assign(a,r.a)),o!=null&&o.a)for(const d of o.a)delete a[d];l&&(e.attributes=a),i[s]=e}n.setState(i,!0)}const kn=(n,t)=>n.subscribeMessage(i=>An(t,i),{type:"subscribe_entities"});function Pn(n,t){const i=n.state;if(i===void 0)return;const{entity_id:s,new_state:e}=t.data;if(e)n.setState({[e.entity_id]:e});else{const r=Object.assign({},i);delete r[s],n.setState(r,!0)}}async function Tn(n){const t=await Sn(n),i={};for(let s=0;s<t.length;s++){const e=t[s];i[e.entity_id]=e}return i}const Rn=(n,t)=>n.subscribeEvents(i=>Pn(t,i),"state_changed"),Mn=n=>Bi(n.haVersion,2022,4,0)?xi(n,"_ent",void 0,kn):xi(n,"_ent",Tn,Rn),In=(n,t)=>Mn(n).subscribe(t);async function On(n){const t=Object.assign({setupRetry:0,createSocket:mn},n),i=await t.createSocket(t);return new vn(i,t)}class rt{constructor(){this.connection=null,this.entitiesListeners=[]}static getInstance(){return rt.instance||(rt.instance=new rt),rt.instance}async connect(t,i){const s=t||localStorage.getItem("ha-url")||window.location.origin,e=i||localStorage.getItem("ha-token");if(!e)throw console.warn("No HA token provided or found in localStorage"),new Error("AUTH_REQUIRED");try{const r=xn(s,e);this.connection=await On({auth:r}),In(this.connection,l=>{this._notifyEntitiesListeners(l)}),this.connection.addEventListener("disconnected",()=>{console.warn("Home Assistant connection lost. Reconnecting...")}),this.connection.addEventListener("ready",()=>{console.log("Home Assistant connection restored.")});const o=await $n(this.connection);return this.connection}catch(r){throw console.error("Failed to connect to Home Assistant",r),r}}onEntitiesUpdate(t){this.entitiesListeners.push(t)}async callService(t,i,s={}){if(!this.connection)throw new Error("No HA connection established");return Cn(this.connection,t,i,s)}async sendMessage(t){if(!this.connection)throw new Error("No HA connection established");return new Promise((i,s)=>{this.connection.sendMessagePromise(t).then(i).catch(s)})}_notifyEntitiesListeners(t){this.entitiesListeners.forEach(i=>i(t))}getConnection(){return this.connection}}const W=rt.getInstance();class ot{constructor(){this._devices=[],this._aiState={status:"idle",lastAction:"",lastCorrection:"",recentAiActions:[],actionHistory:[],voiceStatus:"idle",voiceReply:"",lastStt:""},this._energyStats=[],this._frigateEvents=[],this._criticalFrigateEvent=null,this._lastEntities=null,this._rooms=[{id:"all",name:"全部"}],this._managedDevicesInfo=new Map,this._listeners=[],W.onEntitiesUpdate(t=>{this._lastEntities=t,this._processEntities(t),this._processAIState(t),this._processEnergyStats(t),this._processFrigateEvents(t),this._notifyListeners()}),setInterval(()=>this.refreshManagedDevices(),3e4)}async refreshManagedDevices(){try{const t=await W.sendMessage({type:"smart_agent/get_devices"}),i=(t==null?void 0:t.devices)||t;if(i&&Array.isArray(i)){this._managedDevicesInfo=new Map(i.map(e=>[e.entity_id,{name:e.name,room:e.room}]));const s=new Set;i.forEach(e=>{e.room&&s.add(e.room)}),this._rooms=[{id:"all",name:"全部"},...Array.from(s).map(e=>({id:this._mapRoomToId(e),name:e}))],this._lastEntities&&(this._processEntities(this._lastEntities),this._notifyListeners())}}catch(t){console.warn("[StateManager] Failed to fetch managed devices",t)}}static getInstance(){return ot.instance||(ot.instance=new ot),ot.instance}subscribe(t){this._listeners.push(t),this.refreshManagedDevices(),(this._devices.length>0||this._aiState.lastAction)&&t(this._devices,this._aiState,this._energyStats,this._frigateEvents,this._rooms,this._criticalFrigateEvent)}_processFrigateEvents(t){const i=t["sensor.smart_agent_status"];i&&(i.attributes.frigate_events&&(this._frigateEvents=i.attributes.frigate_events),this._criticalFrigateEvent=i.attributes.critical_frigate_event||null)}_processEnergyStats(t){const i=t["sensor.smart_agent_config"];if(i&&i.attributes.energy_stats){const s=i.attributes.energy_stats;Array.isArray(s)?this._energyStats=[...s]:typeof s=="object"&&(this._energyStats=Object.values(s))}}_processAIState(t){const i=t["sensor.smart_agent_status"],s=t["text.smart_agent_last_action"];if(i){this._aiState.status=i.state;const e=i.attributes.action_history;Array.isArray(e)&&(this._aiState.actionHistory=[...e]),this._aiState.lastCorrection=i.attributes.last_correction||"",this._aiState.recentAiActions=i.attributes.recent_ai_actions||[],this._aiState.voiceStatus=i.attributes.voice_status||"idle",this._aiState.voiceReply=i.attributes.voice_reply||"",this._aiState.lastStt=i.attributes.last_stt||""}s&&s.state!==this._aiState.lastAction&&(this._aiState.lastAction=s.state,s.state&&s.state!=="unknown"&&(this._aiState.actionHistory=[s.state,...this._aiState.actionHistory.filter(e=>e!==s.state)].slice(0,5)))}_processEntities(t){const i=t["sensor.smart_agent_config"];if(i&&i.attributes.device_count!==void 0){const e=this._last_count||0;i.attributes.device_count!==e&&(this._last_count=i.attributes.device_count,this.refreshManagedDevices())}const s=[];for(const[e,r]of Object.entries(t)){const o=this._managedDevicesInfo.get(e.toLowerCase());if(!o)continue;const l=e.split(".")[0],a=o.room||this._guessRoom(e,r);s.push({id:e,type:this._mapDomainToType(l),name:o.name||r.attributes.friendly_name||e,room:a,roomId:this._mapRoomToId(a),state:r.state,brightness:r.attributes.brightness?Math.round(r.attributes.brightness/255*100):void 0,temperature:r.attributes.temperature||r.attributes.current_temperature,humidity:r.attributes.humidity,icon:r.attributes.icon,attributes:r.attributes})}this._devices=s}_mapRoomToId(t){const i=t.toLowerCase();return i.includes("客厅")||i.includes("living")?"living":i.includes("卧室")||i.includes("房")||i.includes("bedroom")?"bedroom":i.includes("书房")||i.includes("study")?"study":i.includes("厨房")||i.includes("kitchen")?"kitchen":i.includes("餐厅")||i.includes("dining")?"dining":i}_mapDomainToType(t){return t==="binary_sensor"?"sensor":t}_guessRoom(t,i){const s=(i.attributes.friendly_name||"").toLowerCase(),e=t.toLowerCase();return s.includes("客厅")||e.includes("living")?"客厅":s.includes("卧室")||s.includes("房")||e.includes("bedroom")?"卧室":s.includes("书房")||e.includes("study")?"书房":s.includes("厨房")||e.includes("kitchen")?"厨房":"未分类"}_notifyListeners(){this._listeners.forEach(t=>t(this._devices,this._aiState,this._energyStats,this._frigateEvents,this._rooms,this._criticalFrigateEvent))}getDevices(){return this._devices}}const Dn=ot.getInstance();class zn{constructor(t,i={}){this._audioCtx=null,this._mediaStream=null,this._processor=null,this._inputNode=null,this._pipelineMsgId=null,this._isRunning=!1,this._audioElem=null,this._vadSilenceCount=0,this.VAD_SILENCE_THRESHOLD=.015,this.VAD_SILENCE_FRAMES=35,this._onHaMessage=s=>{var r,o,l,a,d,h,c,p,u,v,f,I,x,P,C,S,z,y;if(s.data instanceof ArrayBuffer||s.data instanceof Blob)return;let e;try{e=typeof s.data=="string"?JSON.parse(s.data):s.data}catch{return}if(e.id===this._pipelineMsgId)if(e.type==="event"){const _=e.event;switch(_.type){case"stt-end":{const m=((o=(r=_.data)==null?void 0:r.stt_output)==null?void 0:o.text)||"";m&&((a=(l=this._cb).onSttResult)==null||a.call(l,m))}break;case"intent-end":{const m=((u=(p=(c=(h=(d=_.data)==null?void 0:d.intent_output)==null?void 0:h.response)==null?void 0:c.speech)==null?void 0:p.plain)==null?void 0:u.speech)||"";m&&((f=(v=this._cb).onReply)==null||f.call(v,m)),this._emit("tts")}break;case"tts-end":{const m=(x=(I=_.data)==null?void 0:I.tts_output)==null?void 0:x.url;if(m){const b=((C=(P=this._conn._options)==null?void 0:P.auth)==null?void 0:C.hassUrl)||window.location.origin;this._playTts(`${b}${m}`)}this._emit("playing")}break;case"error":{const m=((S=_.data)==null?void 0:S.message)||"语音管道错误";(y=(z=this._cb).onError)==null||y.call(z,m),this._emit("error",m),this._cleanup()}break}}else e.type==="result"&&this._cleanup()},this._conn=t,this._cb=i}get isRunning(){return this._isRunning}async start(){var t,i,s,e,r,o;if(!this._isRunning){this._isRunning=!0,this._vadSilenceCount=0,this._emit("starting");try{this._mediaStream=await navigator.mediaDevices.getUserMedia({audio:{sampleRate:16e3,channelCount:1,echoCancellation:!0,noiseSuppression:!0}});const l=((i=(t=this._conn)._genCmdId)==null?void 0:i.call(t))??Math.floor(Math.random()*1e9);this._pipelineMsgId=l;const a={id:l,type:"assist_pipeline/run",start_stage:"stt",end_stage:"tts",input:{sample_rate:16e3}};(s=this._conn.socket)==null||s.addEventListener("message",this._onHaMessage),this._conn.sendMessage(a),this._emit("stt"),this._audioCtx=new(window.AudioContext||window.webkitAudioContext)({sampleRate:16e3}),this._inputNode=this._audioCtx.createMediaStreamSource(this._mediaStream),this._processor=this._audioCtx.createScriptProcessor(1024,1,1),this._processor.onaudioprocess=d=>{var v;if(!this._isRunning)return;const h=d.inputBuffer.getChannelData(0);let c=0;for(let f=0;f<h.length;f++)c+=h[f]*h[f];const p=Math.sqrt(c/h.length);if(this._cb.onWaveData){const f=[],I=Math.floor(h.length/20);for(let x=0;x<20;x++)f.push(Math.abs(h[x*I]||0));this._cb.onWaveData(f)}if(p<this.VAD_SILENCE_THRESHOLD){if(this._vadSilenceCount++,this._vadSilenceCount>this.VAD_SILENCE_FRAMES){this._stopRecording();return}}else this._vadSilenceCount=0;const u=new Int16Array(h.length);for(let f=0;f<h.length;f++){const I=Math.max(-1,Math.min(1,h[f]));u[f]=I<0?I*32768:I*32767}(v=this._conn.socket)==null||v.send(u.buffer)},this._inputNode.connect(this._processor),this._processor.connect(this._audioCtx.destination)}catch(l){this._isRunning=!1;const a=(e=l.message)!=null&&e.includes("Permission")?"请允许浏览器使用麦克风":`麦克风错误: ${l.message}`;(o=(r=this._cb).onError)==null||o.call(r,a),this._emit("error",a)}}}stop(){this._stopRecording()}_stopRecording(){var t,i,s,e,r;(t=this._processor)==null||t.disconnect(),(i=this._inputNode)==null||i.disconnect(),(s=this._audioCtx)==null||s.close(),this._processor=null,this._inputNode=null,this._audioCtx=null,(e=this._mediaStream)==null||e.getTracks().forEach(o=>o.stop()),this._mediaStream=null,(r=this._conn.socket)==null||r.send(new ArrayBuffer(0)),this._emit("intent")}_playTts(t){this._audioElem&&this._audioElem.pause(),this._audioElem=new Audio(t),this._audioElem.onended=()=>{this._emit("idle"),this._cleanup()},this._audioElem.onerror=()=>{this._emit("idle"),this._cleanup()},this._audioElem.play().catch(()=>{this._emit("idle")})}_emit(t,i){var s,e;(e=(s=this._cb).onStageChange)==null||e.call(s,t,i)}_cleanup(){var t;this._isRunning=!1,(t=this._conn.socket)==null||t.removeEventListener("message",this._onHaMessage),this._pipelineMsgId=null}}class Bn{constructor(t){this._state="stopped",this._audioCtx=null,this._stream=null,this._processor=null,this._source=null,this._activationFrames=0,this.ACTIVATION_THRESHOLD=7,this.ENERGY_THRESHOLD=.02,this._cooldownTimer=null,this.COOLDOWN_MS=8e3,this._onActivated=t}get isListening(){return this._state==="listening"}async start(){if(this._state==="stopped")try{this._stream=await navigator.mediaDevices.getUserMedia({audio:{sampleRate:16e3,channelCount:1,echoCancellation:!0,noiseSuppression:!0}}),this._audioCtx=new(window.AudioContext||window.webkitAudioContext)({sampleRate:16e3}),this._source=this._audioCtx.createMediaStreamSource(this._stream),this._processor=this._audioCtx.createScriptProcessor(2048,1,1),this._processor.onaudioprocess=t=>{if(this._state!=="listening")return;const i=t.inputBuffer.getChannelData(0);let s=0;for(let r=0;r<i.length;r++)s+=i[r]*i[r];Math.sqrt(s/i.length)>this.ENERGY_THRESHOLD?(this._activationFrames++,this._activationFrames>=this.ACTIVATION_THRESHOLD&&(this._activationFrames=0,this._triggerActivation())):this._activationFrames=0},this._source.connect(this._processor),this._processor.connect(this._audioCtx.destination),this._state="listening"}catch(t){console.warn("[AlwaysOnVAD] 麦克风访问失败，免唤醒模式不可用:",t.message)}}pause(){this._state==="listening"&&(this._state="paused")}resume(){this._state==="paused"&&(this._cooldownTimer=setTimeout(()=>{this._state==="paused"&&(this._state="listening",this._activationFrames=0)},this.COOLDOWN_MS))}stop(){var t,i,s,e;this._state="stopped",this._cooldownTimer&&clearTimeout(this._cooldownTimer),(t=this._processor)==null||t.disconnect(),(i=this._source)==null||i.disconnect(),(s=this._audioCtx)==null||s.close(),(e=this._stream)==null||e.getTracks().forEach(r=>r.stop()),this._processor=null,this._source=null,this._audioCtx=null,this._stream=null}_triggerActivation(){this._state="paused",this._onActivated()}}var Nn=Object.defineProperty,Ln=Object.getOwnPropertyDescriptor,O=(n,t,i,s)=>{for(var e=s>1?void 0:s?Ln(t,i):t,r=n.length-1,o;r>=0;r--)(o=n[r])&&(e=(s?o(t,i,e):o(e))||e);return s&&e&&Nn(t,i,e),e};let R=class extends D{constructor(){super(...arguments),this.activeTab="home",this.activeRoomId="all",this.aiState={status:"idle",lastAction:"",lastCorrection:"",recentAiActions:[],actionHistory:[],voiceStatus:"idle",voiceReply:"",lastStt:""},this.devices=[],this.energyStats=[],this.frigateEvents=[],this.criticalEvent=null,this.activeDetailEntity=null,this.isRecording=!1,this.isConnected=!1,this.isConfiguring=!1,this.connectionError="",this.setupStep=0,this.haUrl="",this.haToken="",this.pairingCode="",this.pairingId="",this.authUrl="",this.qrDataUrl="",this.isPairing=!1,this.voiceText="点击开始语音指令",this.voiceReply="",this.waveData=new Array(20).fill(0),this.pipelineStage="idle",this.theme="dark",this._voicePipeline=null,this._alwaysOnVad=null,this.alwaysOnEnabled=!1,this._expressWatchTimer=null,this.rooms=[{id:"all",name:"全部"}],this.scenes=[{id:"sc1",name:"全屋回家",icon:"home",isAi:!0,roomId:"all"},{id:"sc2",name:"全屋离家",icon:"directions_run",isAi:!1,roomId:"all"},{id:"sc_all_off",name:"全屋关灯",icon:"light_off",isAi:!1,roomId:"all"},{id:"sc3",name:"观影模式",icon:"movie",isAi:!0,roomId:"living"},{id:"sc_dinner",name:"用餐模式",icon:"restaurant",isAi:!1,roomId:"living"},{id:"sc4",name:"助眠模式",icon:"bedtime",isAi:!0,roomId:"bedroom"},{id:"sc_night",name:"起夜模式",icon:"nightlight",isAi:!1,roomId:"bedroom"},{id:"sc5",name:"专注工作",icon:"menu_book",isAi:!0,roomId:"study"},{id:"sc_read",name:"阅读模式",icon:"auto_stories",isAi:!1,roomId:"study"}],this.probeStatus=""}firstUpdated(){const n=localStorage.getItem("sa-theme");n&&(this.theme=n,n==="light"&&this.classList.add("theme-light")),Promise.resolve().then(()=>this._initConnection())}_toggleTheme(){this.theme=this.theme==="dark"?"light":"dark",this.theme==="light"?this.classList.add("theme-light"):this.classList.remove("theme-light"),localStorage.setItem("sa-theme",this.theme)}async _initConnection(){const n=new URLSearchParams(window.location.search),t=n.get("ha-url")||n.get("ha_url"),i=n.get("ha-token")||n.get("ha_token");if(t?(this.haUrl=t,localStorage.setItem("ha-url",t)):this.haUrl=localStorage.getItem("ha-url")||"",i?(this.haToken=i,localStorage.setItem("ha-token",i)):this.haToken=localStorage.getItem("ha-token")||"",!this.haUrl){const s=window.location.origin,e=window.location.hostname;s.includes(":8123")||s.includes("homeassistant")?this.haUrl=s:e==="localhost"||e==="127.0.0.1"||s.includes(":5173")?this.haUrl="http://192.168.2.9:8123":this.haUrl=s}if(this.haToken)this._tryConnect();else{this.isConfiguring=!0;const s=window.location.origin.includes(":5173"),e=!!this.haUrl||s;this.setupStep=e?2:1,this._startExpressWatch()}}_startExpressWatch(){this._stopExpressWatch();let n=0;const t=async()=>{if(!(this.isConnected||!this.isConfiguring||this.isPairing)){n++;try{const i=this.haUrl.trim(),s=`${i}/api/smart_agent/pair?probe=1`;this.probeStatus=`探测中 #${n}...`;const r=await(await fetch(s,{signal:AbortSignal.timeout(3e3)})).json();if(r.token){this.probeStatus="收到 Token，正在连接...",this._stopExpressWatch(),this.haToken=r.token;const o=window.location.origin.includes(":5173");this.haUrl=o?"":r.url||i,r.url&&localStorage.setItem("ha-url",r.url),this._tryConnect();return}this.probeStatus=`等待极速配对... (#${n})`}catch(i){console.warn(`[probe #${n}] 失败:`,i.message),this.probeStatus=`探测失败: ${i.message}`}this.isConfiguring&&!this.isConnected&&!this.isPairing&&(this._expressWatchTimer=setTimeout(t,2e3))}};this._expressWatchTimer=setTimeout(t,1500)}_stopExpressWatch(){this._expressWatchTimer!==null&&(clearTimeout(this._expressWatchTimer),this._expressWatchTimer=null)}async _tryConnect(){this._stopExpressWatch();try{this.connectionError="",await W.connect(this.haUrl,this.haToken),localStorage.setItem("ha-url",this.haUrl),localStorage.setItem("ha-token",this.haToken),this.isConnected=!0,this.isConfiguring=!1;const n=W.getConnection();this._voicePipeline=new zn(n,{onStageChange:(t,i)=>{var s;this.pipelineStage=t,t==="stt"?(this.isRecording=!0,this.voiceText="正在聆听中..."):t==="intent"?(this.isRecording=!1,this.voiceText="AI 理解中..."):t==="tts"||t==="playing"?this.voiceText=this.voiceReply||"正在生成回复...":t==="idle"?(this.isRecording=!1,this.voiceText=this.alwaysOnEnabled?"随时说话...":"点击开始语音指令",this.waveData=new Array(20).fill(0),setTimeout(()=>{this.voiceReply=""},8e3),this.alwaysOnEnabled&&((s=this._alwaysOnVad)==null||s.resume())):t==="error"&&(this.isRecording=!1,this.voiceText=this.alwaysOnEnabled?"出错了，继续监听中...":i||"出现错误，请重试",this.waveData=new Array(20).fill(0),this.alwaysOnEnabled&&setTimeout(()=>{var e;return(e=this._alwaysOnVad)==null?void 0:e.resume()},2e3))},onSttResult:t=>{this.voiceText=`"${t}"`},onReply:t=>{this.voiceReply=t},onError:t=>{console.error("[VoicePipeline]",t),this.voiceText=t,this.isRecording=!1},onWaveData:t=>{this.waveData=[...t]},onVadActivated:()=>{}}),this._alwaysOnVad=new Bn(async()=>{!this._voicePipeline||this._voicePipeline.isRunning||(this.voiceText="检测到语音，正在识别...",await this._voicePipeline.start())}),Dn.subscribe((t,i,s,e,r,o)=>{this.devices=[...t],this.aiState={...i},this.energyStats=[...s],this.frigateEvents=[...e],this.rooms=[...r],this.criticalEvent=o})}catch(n){console.error("Connection failed",n),this.isConnected=!1,this.isConfiguring=!0,this.connectionError=n.message==="AUTH_REQUIRED"?"访问令牌无效或已过期":"无法连接到 Home Assistant 服务器"}}_saveConfig(){this._tryConnect()}async _toggleVoice(){if(!this._voicePipeline){this.voiceText="语音功能初始化中...";return}this._voicePipeline.isRunning?this._voicePipeline.stop():await this._voicePipeline.start()}async _startRecording(){await this._toggleVoice()}async _stopRecording(){var n;(n=this._voicePipeline)==null||n.stop()}async _toggleAlwaysOn(){this._alwaysOnVad&&(this.alwaysOnEnabled?(this._alwaysOnVad.stop(),this.alwaysOnEnabled=!1,this.voiceText="点击开始语音指令"):(await this._alwaysOnVad.start(),this.alwaysOnEnabled=!0,this.voiceText="随时说话..."))}_renderActiveRoomView(){const n=this.activeRoomId,t=n==="all"?this.devices:this.devices.filter(r=>r.roomId===n);if(t.length===0&&n!=="all")return g`
        <div style="text-align: center; padding: 100px 20px; color: rgba(255,255,255,0.15);">
          <span class="icon-main" style="font-size: 64px; margin-bottom: 24px; display: block; opacity: 0.1;">devices_other</span>
          <div style="font-size: 16px; font-weight: 700;">该区域暂无托管设备</div>
        </div>
      `;const i=this.scenes.filter(r=>r.roomId===n||n==="all"&&r.isAi),s=this.devices.filter(r=>r.type==="scene"&&(n==="all"||r.roomId===n)),e=[{id:"light",name:"照明",icon:"lightbulb"},{id:"climate",name:"环境",icon:"thermostat"},{id:"cover",name:"遮蔽",icon:"curtains"},{id:"sensor",name:"感应",icon:"sensors"},{id:"other",name:"其他",icon:"more_horiz"}];return g`
      <div class="room-content" style="padding-top: 0;">
        <!-- 场景区 -->
        ${i.length>0||s.length>0?g`
          <div class="category-group">
            <div class="section-label">
              <span class="icon-main">auto_awesome</span> 场景模式
            </div>
            <div class="scene-grid-orb">
              ${i.map(r=>g`<scene-card .scene="${r}" .isAiRecommended="${r.isAi}"></scene-card>`)}
              ${s.map(r=>g`<scene-card .scene="${r}" .isAiRecommended="${!0}"></scene-card>`)}
            </div>
          </div>
        `:""}

        <!-- 设备分类区 -->
        ${e.map(r=>{const o=t.filter(a=>r.id==="other"?!["light","climate","cover","sensor","scene"].includes(a.type):a.type===r.id);if(o.length===0)return"";let l=`${o.length} 个设备`;if(r.id==="light"){const a=o.filter(d=>d.state==="on").length;l=a===0?"灯全部关了":`${a} 盏灯开启中`}return g`
            <div class="category-group">
              <div class="section-label">
                <span class="icon-main">${r.icon}</span> ${r.name} <span style="opacity:0.4; font-size:13px; font-weight:600; margin-left:8px;">| ${l}</span>
              </div>
              <div class="device-grid-orb">
                ${o.map(a=>{const d=this.aiState.recentAiActions.includes(a.id);return a.type==="light"?g`<light-card .device="${a}" .isAiControlled="${d}"></light-card>`:a.type==="climate"?g`<climate-card .device="${a}" .isAiControlled="${d}"></climate-card>`:a.type==="cover"?g`<cover-card .device="${a}" .isAiControlled="${d}"></cover-card>`:a.type==="sensor"?g`<sensor-card .device="${a}"></sensor-card>`:g`<generic-device-card .device="${a}" .isAiControlled="${d}"></generic-device-card>`})}
              </div>
            </div>
          `})}
      </div>
    `}async _handleServiceCall(n){var s;const{detail:t}=n,i=(s=t.data)==null?void 0:s.entity_id;i&&this.aiState.recentAiActions.includes(i)&&W.callService("smart_agent","report_correction",{entity_id:i,reason:"中控屏手动覆盖"});try{await W.callService(t.domain,t.service,t.data)}catch(e){console.error("[ServiceCall] 指令发送失败:",e)}}async _startPairing(){if(!this.isPairing){this._stopExpressWatch(),this.isPairing=!0,this.pairingId="",this.pairingCode="",this.authUrl="",this.qrDataUrl="",this.connectionError="";try{let n=this.haUrl.trim();n&&!n.startsWith("http")&&(n="http://"+n),n.endsWith("/")&&(n=n.slice(0,-1));const t=await fetch(`${n}/api/smart_agent/pair`);if(!t.ok)throw new Error("API_FAILED");const i=await t.json();if(i.token){this.haToken=i.token;const s=window.location.origin.includes(":5173");this.haUrl=s?"":i.url||n,i.url&&localStorage.setItem("ha-url",i.url),this.isPairing=!1,this._tryConnect();return}this.pairingId=i.id||"",this.pairingCode=i.code||"",this.authUrl=i.auth_url||"",this.authUrl&&(this.qrDataUrl=await Rs.toDataURL(this.authUrl,{width:200,margin:1,color:{dark:"#1a1a2e",light:"#ffffff"}})),this.setupStep=3,this._pollPairingStatus(n)}catch(n){console.error("Pairing failed",n),this.connectionError="无法连接到配对服务器，请检查地址是否正确",this.setupStep=1,this.isPairing=!1}}}async _pollPairingStatus(n){if(this.isPairing){if(!this.pairingId||this.pairingId==="FAST_PAIR"){console.warn("[pairing] 无效的 pairingId，停止轮询:",this.pairingId),this.isPairing=!1;return}try{const i=await(await fetch(`${n}/api/smart_agent/pair?id=${this.pairingId}`)).json();if(i.token){this.haToken=i.token;const s=window.location.origin.includes(":5173");this.haUrl=s?"":i.url||n,i.url&&localStorage.setItem("ha-url",i.url),this.isPairing=!1,this.setupStep=0,this._tryConnect()}else i.error==="EXPIRED"?(this.connectionError='配对码已过期，请重新点击"一键连接"',this.isPairing=!1,this.setupStep=2):setTimeout(()=>this._pollPairingStatus(n),2e3)}catch(t){console.warn("Polling pairing status failed",t),setTimeout(()=>this._pollPairingStatus(n),5e3)}}}_renderConfigScreen(){return g`
      <div style="display:flex; height:100vh; align-items:center; justify-content:center; padding: 20px; box-sizing: border-box; overflow: hidden;">
        <glass-card variant="elevated" style="width: 100%; max-width: 480px; min-height: 420px; padding: 48px; display: flex; flex-direction: column; justify-content: center; gap: 40px; position: relative; border-radius: 32px;">
          
          <!-- 智能引导头部 -->
          <div style="text-align: center;">
            <div style="font-size: 42px; font-weight: 900; background: linear-gradient(135deg, #B388FF 0%, #82B1FF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; letter-spacing: -1.5px;">
              SmartAgent
            </div>
            <div style="opacity: 0.5; font-size: 15px; font-weight: 600; letter-spacing: 1px;">
              ${this.setupStep===1?"配置服务器地址":this.setupStep===2?"准备就绪":"安全授权中"}
            </div>
          </div>

          ${this.setupStep===1?g`
            <!-- 步骤 1: HA 地址输入 (仅当探测失败时显示) -->
            <div style="display: flex; flex-direction: column; gap: 24px; animation: fadeIn 0.4s ease;">
              <div style="text-align: center; font-size: 14px; opacity: 0.7;">无法自动发现服务器，请手动输入</div>
              <input 
                type="text" 
                .value="${this.haUrl}" 
                @input="${n=>this.haUrl=n.target.value}"
                style="width: 100%; box-sizing: border-box; background: rgba(255,255,255,0.03); border: 2px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 20px; color: white; font-family: inherit; font-size: 16px; outline: none; text-align: center;"
                placeholder="例如: 192.168.1.100:8123"
              >
              <button 
                @click="${()=>this.setupStep=2}"
                style="background: var(--glass-primary); border: none; border-radius: 20px; padding: 20px; color: white; font-weight: 800; font-size: 18px; cursor: pointer; box-shadow: 0 10px 30px var(--glass-primary-glow);"
              >
                继续
              </button>
            </div>
          `:this.setupStep===2?g`
            <!-- 步骤 2: 真正的“一键连接”入口 -->
            <div style="display: flex; flex-direction: column; gap: 28px; animation: zoomIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);">
              
              <div style="text-align: center; background: rgba(255,255,255,0.03); padding: 16px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="font-size: 12px; opacity: 0.4; margin-bottom: 4px;">已自动发现服务器</div>
                <div style="font-size: 14px; font-family: 'JetBrains Mono'; opacity: 0.8;">
                  ${this.haUrl||"192.168.2.9:8123（通过代理）"}
                </div>
              </div>

              <button 
                @click="${this._startPairing}"
                style="background: linear-gradient(135deg, var(--glass-primary) 0%, #7C4DFF 100%); border: none; border-radius: 24px; padding: 32px; color: white; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 12px; transition: all 0.4s; box-shadow: 0 20px 40px rgba(179,136,255,0.3); position: relative; overflow: hidden;"
                onmouseover="this.style.transform='scale(1.02) translateY(-4px)'; this.style.boxShadow='0 25px 50px rgba(179,136,255,0.4)'"
                onmouseout="this.style.transform='none'; this.style.boxShadow='0 20px 40px rgba(179,136,255,0.3)'"
              >
                <!-- 动态光效环 -->
                <div class="pulse-ring"></div>
                
                <span class="icon-main" style="font-size: 48px; position: relative; z-index: 1;">bolt</span>
                <div style="font-weight: 900; font-size: 22px; position: relative; z-index: 1;">一键连接</div>
                <div style="font-size: 13px; opacity: 0.8; font-weight: 500; position: relative; z-index: 1;">免扫码或扫码一键授权</div>
              </button>

              <div @click="${()=>this.setupStep=4}" style="text-align: center; opacity: 0.3; font-size: 13px; cursor: pointer; font-weight: 500; text-decoration: underline;">
                手动输入令牌 (高级)
              </div>
              
              <div @click="${()=>this.setupStep=1}" style="text-align: center; margin-top: -10px; opacity: 0.2; font-size: 11px; cursor: pointer;">
                修改服务器地址
              </div>

              ${this.probeStatus?g`
                <div style="text-align: center; font-size: 11px; opacity: 0.35; margin-top: -4px; font-family: 'JetBrains Mono', monospace;">
                  ${this.probeStatus}
                </div>
              `:""}
            </div>
          `:this.setupStep===3?this._renderPairingScreen():this._renderManualInput()}

          ${this.connectionError?g`
            <div style="position: absolute; bottom: 24px; left: 48px; right: 48px; text-align: center; color: #FF5252; font-size: 13px; background: rgba(255, 82, 82, 0.1); padding: 10px; border-radius: 12px; animation: shake 0.4s ease;">
              <span class="icon-main" style="font-size: 14px; vertical-align: middle; margin-right: 6px;">error</span>
              ${this.connectionError}
            </div>
          `:""}
        </glass-card>

        <style>
          @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
          @keyframes zoomIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
          @keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-6px); } 75% { transform: translateX(6px); } }
          
          .pulse-ring {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 100%; height: 100%;
            background: rgba(255,255,255,0.2);
            border-radius: 24px;
            animation: pulse 2s infinite;
            z-index: 0;
          }
          @keyframes pulse {
            0% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; }
            100% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
          }
        </style>
      </div>
    `}_renderManualInput(){return g`
      <div style="display: flex; flex-direction: column; gap: 24px; animation: slideIn 0.4s ease;">
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <label style="font-size: 12px; opacity: 0.4; font-weight: 700; text-transform: uppercase;">长期访问令牌 (Token)</label>
          <textarea 
            .value="${this.haToken}" 
            @input="${n=>this.haToken=n.target.value}"
            style="width: 100%; box-sizing: border-box; background: rgba(255,255,255,0.03); border: 2px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 20px; color: white; font-family: inherit; font-size: 13px; height: 160px; resize: none; outline: none;"
            placeholder="在此粘贴来自 HA 的令牌..."
          ></textarea>
        </div>
        <button 
          @click="${this._saveConfig}"
          style="background: var(--glass-primary); border: none; border-radius: 20px; padding: 20px; color: white; font-weight: 800; font-size: 18px; cursor: pointer;"
        >
          完成并同步
        </button>
        <div @click="${()=>this.setupStep=2}" style="text-align: center; opacity: 0.4; font-size: 13px; cursor: pointer;">
          ← 返回一键配对
        </div>
      </div>
    `}_renderPairingScreen(){return g`
      <div style="display: flex; flex-direction: column; gap: 20px; animation: fadeIn 0.4s ease;">
        
        <!-- 顶部：配对码数字（最醒目） -->
        <div style="text-align: center;">
          <div style="font-size: 11px; opacity: 0.4; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">手机访问 HA 输入配对码</div>
          <div style="display: flex; gap: 8px; justify-content: center;">
            ${(this.pairingCode||"").split("").map(n=>g`
              <div style="width: 38px; height: 52px; background: rgba(179,136,255,0.1); border: 2px solid rgba(179,136,255,0.3); border-radius: 12px; font-size: 26px; font-weight: 900; display: flex; align-items: center; justify-content: center; font-family: 'JetBrains Mono', monospace; color: #B388FF; box-shadow: 0 4px 16px rgba(179,136,255,0.2);">
                ${n}
              </div>
            `)}
          </div>
        </div>

        <!-- 中间：二维码（本地生成，不依赖外部API） -->
        <div style="display: flex; gap: 16px; align-items: center;">
          <div style="background: white; padding: 8px; border-radius: 16px; width: 100px; height: 100px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(179,136,255,0.2);">
            ${this.qrDataUrl?g`<img src="${this.qrDataUrl}" style="width:100%; height:100%;" alt="QR">`:g`<div style="font-size:11px; color:#888; text-align:center;">生成中...</div>`}
          </div>
          <div style="flex: 1; font-size: 12px; opacity: 0.6; line-height: 1.8;">
            <div style="font-weight: 700; opacity: 1; color: var(--glass-ai); font-size: 13px; margin-bottom: 6px;">如何操作</div>
            <div>① 手机扫码 <span style="opacity:0.4;">或</span></div>
            <div>① 手机打开 HA，进入开发者工具</div>
            <div>② 找到 SmartAgent → <code style="background:rgba(255,255,255,0.05); padding: 2px 6px; border-radius:4px;">配对确认</code></div>
            <div>③ 输入上方 <strong style="color:#B388FF">6位数字</strong> 后确认</div>
          </div>
        </div>

        <!-- 等待状态 -->
        <div style="background: rgba(179,136,255,0.05); padding: 14px 20px; border-radius: 16px; border: 1px solid rgba(179,136,255,0.1); display: flex; align-items: center; gap: 12px;">
          <div class="loader"></div>
          <div>
            <div style="font-size: 13px; font-weight: 600; color: var(--glass-ai);">等待手机确认...</div>
            <div style="font-size: 11px; opacity: 0.4; margin-top: 2px;">配对成功后将自动连接，下次打开无需再次授权</div>
          </div>
        </div>

        <div @click="${()=>{this.setupStep=2,this.isPairing=!1}}" 
             style="text-align: center; opacity: 0.3; font-size: 12px; cursor: pointer; padding: 4px;">
          取消并返回
        </div>
      </div>
    `}render(){return this.isConfiguring?this._renderConfigScreen():this.isConnected?g`
      <div class="container" 
        @service-call="${this._handleServiceCall}"
        @show-detail="${n=>{const t=this.devices.find(i=>i.id===n.detail.entityId);t&&(this.activeDetailEntity=t)}}"
      >
        <!-- 1. 侧边栏：AI 状态模块 -->
        <div class="sidebar">
          <div class="ai-brain-module">
            <div style="display:flex; align-items:center; gap:16px; margin-bottom:12px;">
              <span class="icon-main" style="color:var(--ai-purple); font-size:32px;">auto_awesome</span>
              <div style="font-size:18px; font-weight:900;">AI 领航员</div>
            </div>
            <ai-status-panel .aiState="${this.aiState}"></ai-status-panel>
          </div>
        </div>

        <!-- 2. 顶栏：状态显示 (Clock & Weather) -->
        <div class="topbar">
          <div style="display:flex; align-items:center; gap:24px;">
            <clock-widget></clock-widget>
            <div style="width:1px; height:24px; background:var(--t-divider);"></div>
            <weather-widget></weather-widget>
          </div>
          
          <div class="status-group" style="display:flex; align-items:center; gap:16px;">
            <div class="status-item">
              <span class="status-label">今日</span>
              <span class="status-value">3.4kWh</span>
            </div>
            <!-- 主题切换按钮 -->
            <button
              @click="${()=>this._toggleTheme()}"
              title="${this.theme==="dark"?"切换浅色模式":"切换深色模式"}"
              style="
                width:36px; height:36px; border-radius:50%;
                border:1px solid var(--t-input-border);
                background:var(--t-input-bg);
                color:var(--t-text-sec);
                display:flex; align-items:center; justify-content:center;
                cursor:pointer; font-family:'Material Symbols Outlined';
                font-size:20px; transition:all 0.3s;
              "
            >${this.theme==="dark"?"light_mode":"dark_mode"}</button>
          </div>
        </div>

        <!-- 3. 主区域：分房间视图 -->
        <div class="main">
          <div class="room-content" style="padding-bottom: 0;">
            <!-- 房间切换选项卡 (ORB Style) -->
            <div class="room-tabs">
              ${this.rooms.map(n=>g`
                <div 
                  class="room-tab ${this.activeRoomId===n.id?"active":""}"
                  @click="${()=>this.activeRoomId=n.id}"
                >${n.name}</div>
              `)}
            </div>
          </div>
          ${this._renderActiveRoomView()}
        </div>

        <!-- 4. 底栏：语音交互 -->
        <div class="voice">
          <div class="voice-interactive-zone">
            <voice-bar 
              .isRecording="${this.isRecording}" 
              .status="${this.pipelineStage==="intent"||this.pipelineStage==="tts"?"processing":this.pipelineStage==="playing"?"done":this.pipelineStage}"
              .text="${this.voiceText}"
              .waveData="${this.waveData}"
              @toggle-voice="${this._toggleVoice}"
            ></voice-bar>
          </div>
          <!-- 免唤醒模式开关 -->
          <button
            class="always-on-btn ${this.alwaysOnEnabled?"active":""}"
            @click="${this._toggleAlwaysOn}"
            title="${this.alwaysOnEnabled?"关闭免唤醒模式":"开启免唤醒模式"}"
          >
            <span class="icon-main">${this.alwaysOnEnabled?"hearing":"hearing_disabled"}</span>
          </button>
        </div>

          <!-- AI Reply Overlay (Ambient) -->
          ${this.voiceReply?g`
            <div style="position:absolute; bottom:130px; left:50%; transform:translateX(-50%); width:90%; background:linear-gradient(90deg, var(--ai-purple), var(--ai-cyan)); padding:20px 40px; border-radius:32px; box-shadow:0 15px 50px rgba(0,229,255,0.3); animation:slideUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); display:flex; align-items:center; gap:20px;">
              <span class="icon-main" style="color:white; font-size:32px;">auto_awesome</span>
              <span style="font-size:18px; font-weight:800; color:white;">${this.voiceReply}</span>
            </div>
          `:""}
        </div>

        <!-- 5. 关键视觉事件大图弹出 (Critical Event Overlay) -->
        ${this.criticalEvent?g`
          <div class="critical-overlay">
            <div class="critical-card">
              <div class="critical-header">
                <div style="display:flex; align-items:center; gap:12px;">
                  <span class="pulse-dot" style="background:#ff5252;"></span>
                  <span style="font-weight:900; color:#ff5252; letter-spacing:1px; font-size:12px;">CRITICAL EVENT</span>
                </div>
                <div class="critical-time" style="font-size:12px; opacity:0.4; font-weight:700;">
                  ${new Date(this.criticalEvent.time*1e3).toLocaleTimeString()}
                </div>
              </div>
              
              <div class="critical-camera-name" style="margin: 12px 0; font-size:18px; font-weight:800; display:flex; align-items:center; gap:8px;">
                <span class="icon-main" style="font-size:24px; opacity:0.5;">videocam</span>
                ${this.criticalEvent.camera_name}
              </div>

              <div class="critical-snapshot-box" style="width:100%; border-radius:24px; overflow:hidden; position:relative; aspect-ratio:16/9; background:#000;">
                <img src="${this.haUrl}${this.criticalEvent.snapshot}" style="width:100%; height:100%; object-fit:cover;" alt="Critical Snapshot">
                <div class="snapshot-label" style="position:absolute; bottom:16px; left:16px; background:rgba(0,0,0,0.6); padding:6px 12px; border-radius:8px; font-size:11px; font-weight:700; backdrop-filter:blur(10px);">检测到人员停留</div>
              </div>

              <div class="critical-ai-insight" style="margin-top:20px; padding:20px; background:rgba(179,136,255,0.08); border-radius:20px; border:1px solid rgba(179,136,255,0.15); display:flex; gap:16px; align-items:flex-start;">
                <span class="icon-main" style="color:var(--ai-purple); font-size:32px;">psychology</span>
                <div style="flex:1;">
                  <div style="font-size:10px; opacity:0.5; font-weight:900; text-transform:uppercase; margin-bottom:6px; letter-spacing:1px;">AI INSIGHT</div>
                  <div style="font-size:14px; font-weight:600; line-height:1.6; color:rgba(255,255,255,0.9);">
                    门口发现可疑停留，置信度 ${Math.round(this.criticalEvent.score*100)}%。建议开启玄关灯并发出语音询问。
                  </div>
                </div>
              </div>

              <div class="critical-actions" style="margin-top:24px; display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                <button class="critical-btn secondary" 
                  style="padding:18px; border-radius:16px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:white; font-weight:800; font-size:15px; cursor:pointer;"
                  @click="${()=>this.criticalEvent=null}">忽略此事件</button>
                <button class="critical-btn primary" 
                  style="padding:18px; border-radius:16px; border:none; background:var(--ai-purple); color:white; font-weight:800; font-size:15px; cursor:pointer; box-shadow:0 8px 24px rgba(179,136,255,0.3);"
                  @click="${()=>{W.callService("smart_agent","manual_inference",{trigger:`[视觉主动] ${this.criticalEvent.camera_name} 发现人员长时间停留`}),this.criticalEvent=null}}">允许 AI 处理</button>
              </div>
            </div>
          </div>
        `:""}

        <!-- 6. 设备深度控制面板 (Detail Overlay) -->
        ${this.activeDetailEntity?g`
          <div class="critical-overlay" @click="${()=>this.activeDetailEntity=null}">
            <div class="detail-card" @click="${n=>n.stopPropagation()}">
              <div class="detail-header">
                <div style="display:flex; align-items:center; gap:16px;">
                  <div class="icon-box" style="width:48px; height:48px; border-radius:14px; background:rgba(255,255,255,0.05); display:flex; align-items:center; justify-content:center;">
                    <span class="icon-main" style="font-size:24px;">
                      ${this.activeDetailEntity.type==="light"?"lightbulb":"ac_unit"}
                    </span>
                  </div>
                  <div>
                    <div style="font-size:18px; font-weight:800;">${this.activeDetailEntity.name}</div>
                    <div style="font-size:12px; opacity:0.4;">${this.activeDetailEntity.room}</div>
                  </div>
                </div>
                <button 
                  style="width:40px; height:40px; border-radius:50%; border:none; background:rgba(255,255,255,0.05); color:white; cursor:pointer;"
                  @click="${()=>this.activeDetailEntity=null}"
                >
                  <span class="icon-main">close</span>
                </button>
              </div>

              <div class="detail-content" style="margin-top:24px;">
                ${this.activeDetailEntity.type==="light"?g`
                  <light-detail-panel .device="${this.activeDetailEntity}"></light-detail-panel>
                `:this.activeDetailEntity.type==="climate"?g`
                  <climate-detail-panel .device="${this.activeDetailEntity}"></climate-detail-panel>
                `:""}
              </div>
            </div>
          </div>
        `:""}
      </div>
    `:g`<div style="display:flex; height:100vh; align-items:center; justify-content:center;">正在连接...</div>`}};R.styles=B`
    /* ═══════════════════════════════════════════
       深色主题（默认）
    ═══════════════════════════════════════════ */
    :host {
      display: block;
      height: 100vh; width: 100vw;
      font-family: 'HarmonyOS Sans SC', 'Inter', system-ui, sans-serif;
      overflow: hidden;
      /* PAD 布局尺寸 */
      --sidebar-width: 280px;
      --topbar-height: 72px;
      --voicebar-height: 56px;

      /* ── 深色主题色板 ── */
      --t-bg: #080B12;
      --t-bg-grad1: rgba(179, 136, 255, 0.07);
      --t-bg-grad2: rgba(0, 229, 255, 0.05);
      --t-sidebar: rgba(0, 0, 0, 0.18);
      --t-topbar: rgba(8, 11, 18, 0.6);
      --t-voicebar: rgba(8, 11, 18, 0.7);
      --t-card: rgba(255, 255, 255, 0.06);
      --t-card-border: rgba(255, 255, 255, 0.09);
      --t-card-hover: rgba(255, 255, 255, 0.09);
      --t-card-on: rgba(92, 219, 149, 0.13);
      --t-card-on-border: rgba(92, 219, 149, 0.40);
      --t-card-on-glow: rgba(92, 219, 149, 0.20);
      --t-text: #F0F2F5;
      --t-text-sec: rgba(240, 242, 245, 0.55);
      --t-text-hint: rgba(240, 242, 245, 0.30);
      --t-divider: rgba(255, 255, 255, 0.07);
      --t-input-bg: rgba(255, 255, 255, 0.06);
      --t-input-border: rgba(255, 255, 255, 0.10);
      --t-track: rgba(255, 255, 255, 0.08);
      --t-toggle-off: rgba(255, 255, 255, 0.08);
      --t-toggle-off-border: rgba(255, 255, 255, 0.06);
      --t-nav-item: rgba(255, 255, 255, 0.03);
      --t-nav-border: rgba(255, 255, 255, 0.05);
      --t-detail-bg: rgba(10, 12, 20, 0.96);
      --t-detail-card: rgba(255, 255, 255, 0.05);

      /* ── 品牌色 ── */
      --glass-primary: #7AB8FF;
      --glass-primary-glow: rgba(122, 184, 255, 0.35);
      --glass-bg: var(--t-card);
      --glass-border: var(--t-card-border);
      --ai-purple: #B388FF;
      --ai-cyan: #00E5FF;

      /* ── 应用 ── */
      background: var(--t-bg);
      background-image:
        radial-gradient(circle at 12% 20%, var(--t-bg-grad1) 0%, transparent 42%),
        radial-gradient(circle at 88% 82%, var(--t-bg-grad2) 0%, transparent 42%);
      color: var(--t-text);
    }

    /* ═══════════════════════════════════════════
       浅色主题
    ═══════════════════════════════════════════ */
    :host(.theme-light) {
      --t-bg: #EEF1F8;
      --t-bg-grad1: rgba(99, 102, 241, 0.06);
      --t-bg-grad2: rgba(14, 165, 233, 0.05);
      --t-sidebar: rgba(255, 255, 255, 0.88);
      --t-topbar: rgba(238, 241, 248, 0.85);
      --t-voicebar: rgba(255, 255, 255, 0.90);
      --t-card: rgba(255, 255, 255, 0.78);
      --t-card-border: rgba(0, 0, 0, 0.06);
      --t-card-hover: rgba(255, 255, 255, 0.96);
      --t-card-on: rgba(22, 163, 74, 0.10);
      --t-card-on-border: rgba(22, 163, 74, 0.32);
      --t-card-on-glow: rgba(22, 163, 74, 0.12);
      --t-text: #1A1D26;
      --t-text-sec: rgba(26, 29, 38, 0.55);
      --t-text-hint: rgba(26, 29, 38, 0.32);
      --t-divider: rgba(0, 0, 0, 0.07);
      --t-input-bg: rgba(0, 0, 0, 0.04);
      --t-input-border: rgba(0, 0, 0, 0.09);
      --t-track: rgba(0, 0, 0, 0.09);
      --t-toggle-off: rgba(0, 0, 0, 0.09);
      --t-toggle-off-border: rgba(0, 0, 0, 0.07);
      --t-nav-item: rgba(0, 0, 0, 0.04);
      --t-nav-border: rgba(0, 0, 0, 0.06);
      --t-detail-bg: rgba(238, 241, 248, 0.97);
      --t-detail-card: rgba(255, 255, 255, 0.80);

      --glass-primary: #5B6CF9;
      --glass-primary-glow: rgba(91, 108, 249, 0.25);
      --glass-bg: var(--t-card);
      --glass-border: var(--t-card-border);
      --ai-purple: #7C4DFF;
      --ai-cyan: #0EA5E9;

      background: var(--t-bg);
      background-image:
        radial-gradient(circle at 12% 20%, var(--t-bg-grad1) 0%, transparent 42%),
        radial-gradient(circle at 88% 82%, var(--t-bg-grad2) 0%, transparent 42%);
      color: var(--t-text);
    }

    .container {
      display: grid;
      grid-template-areas:
        "sidebar topbar"
        "sidebar main"
        "sidebar voice";
      grid-template-columns: var(--sidebar-width) 1fr;
      grid-template-rows: var(--topbar-height) 1fr var(--voicebar-height);
      height: 100vh;
      padding: 0;
      gap: 0;
      box-sizing: border-box;
    }

    /* 侧边栏：AI 状态面板 */
    .sidebar {
      grid-area: sidebar;
      display: flex;
      flex-direction: column;
      background: var(--t-sidebar);
      border-right: 1px solid var(--t-divider);
      padding: 24px;
      overflow: hidden;
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
    }

    .ai-brain-module {
      display: flex;
      flex-direction: column;
      gap: 20px;
      height: 100%;
    }

    /* 顶栏 (ORB Style) */
    .topbar {
      grid-area: topbar;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 32px;
      background: var(--t-topbar);
      border-bottom: 1px solid var(--t-divider);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
    }

    /* 主区域 (ORB Style) */
    .main {
      grid-area: main;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      scrollbar-width: none;
      background: transparent;
    }
    .main::-webkit-scrollbar { display: none; }

    .room-content {
      padding: 32px;
      display: flex;
      flex-direction: column;
      gap: 40px;
    }

    .room-tabs {
      display: flex;
      gap: 40px;
      margin-bottom: 8px;
      border-bottom: 1px solid var(--t-divider);
    }

    .room-tab {
      font-size: 15px;
      font-weight: 800;
      color: var(--t-text-hint);
      cursor: pointer;
      transition: all 0.3s;
      position: relative;
      padding: 12px 0;
    }

    .room-tab.active {
      color: var(--t-text);
    }

    .room-tab.active::after {
      content: '';
      position: absolute;
      bottom: 0; left: -4px; right: -4px;
      height: 4px;
      background: var(--ai-cyan);
      border-radius: 99px;
      box-shadow: 0 0 15px var(--ai-cyan);
    }

    .category-group {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .section-label {
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--t-text-hint);
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 800;
      margin-left: 4px;
    }

    .device-grid-orb {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      grid-auto-rows: 148px;
      gap: 14px;
    }

    .scene-grid-orb {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      grid-auto-rows: 56px; /* 场景按钮横向排布，高度 56px */
      gap: 12px;
    }

    .icon-main { 
      font-family: 'Material Symbols Outlined';
      font-weight: normal;
      font-style: normal;
      font-size: 24px;
      line-height: 1;
      letter-spacing: normal;
      text-transform: none;
      display: inline-block;
      white-space: nowrap;
      word-wrap: normal;
      direction: ltr;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeLegibility;
      font-feature-settings: 'liga';
    }

    .loader {
      width: 20px; height: 20px;
      border: 3px solid rgba(255,255,255,0.1);
      border-top: 3px solid var(--glass-primary);
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

    @keyframes scan {
      0% { transform: translateY(-100%); opacity: 0; }
      50% { opacity: 0.5; }
      100% { transform: translateY(100%); opacity: 0; }
    }

      .scanning-line {
        position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, var(--glass-ai), transparent);
        animation: scan 3s linear infinite;
        z-index: 5;
        pointer-events: none;
      }

      .voice {
      grid-area: voice;
      display: flex;
      align-items: center;
      padding: 0 32px;
      background: var(--t-voicebar);
      border-top: 1px solid var(--t-divider);
      justify-content: space-between;
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
    }

    .voice-interactive-zone {
      flex: 1;
      display: flex;
      align-items: center;
      height: 100%;
    }

    .always-on-btn {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: 1px solid var(--t-input-border);
      background: var(--t-input-bg);
      color: var(--t-text-sec);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.25s ease;
      margin-left: 12px;
    }
    .always-on-btn .icon-main {
      font-size: 18px;
    }
    .always-on-btn:hover {
      background: rgba(255,255,255,0.12);
      color: rgba(255,255,255,0.8);
    }
    .always-on-btn.active {
      background: linear-gradient(135deg, var(--ai-purple), var(--ai-cyan));
      border-color: transparent;
      color: white;
      box-shadow: 0 0 12px rgba(100, 181, 246, 0.5);
      animation: pulse-ring 2s ease-in-out infinite;
    }
    @keyframes pulse-ring {
      0%, 100% { box-shadow: 0 0 12px rgba(100,181,246,0.5); }
      50% { box-shadow: 0 0 20px rgba(100,181,246,0.9), 0 0 36px rgba(100,181,246,0.3); }
    }

    /* 关键事件弹窗样式 */
      .critical-overlay {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.75);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.3s ease;
      }

      .critical-card {
        width: 640px;
        background: var(--t-detail-bg, #0a0c14);
        border: 1px solid rgba(255, 82, 82, 0.3);
        border-radius: 40px;
        padding: 32px;
        box-shadow: 0 40px 100px rgba(0,0,0,0.6), 0 0 60px rgba(255, 82, 82, 0.15);
        animation: scaleUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      }

      @keyframes scaleUp {
        from { transform: scale(0.9); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
      }

      .critical-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
      }

      .critical-btn:active {
        transform: scale(0.96);
      }

      .detail-card {
        width: 520px;
        background: #0a0c14;
        border: 1px solid var(--glass-border);
        border-radius: 40px;
        padding: 32px;
        box-shadow: 0 40px 100px rgba(0,0,0,0.8);
        animation: scaleUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      }

      .detail-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
    `;O([M()],R.prototype,"activeTab",2);O([M()],R.prototype,"activeRoomId",2);O([M()],R.prototype,"aiState",2);O([M()],R.prototype,"devices",2);O([M()],R.prototype,"energyStats",2);O([M()],R.prototype,"frigateEvents",2);O([M()],R.prototype,"criticalEvent",2);O([M()],R.prototype,"activeDetailEntity",2);O([M()],R.prototype,"isRecording",2);O([M()],R.prototype,"isConnected",2);O([M()],R.prototype,"isConfiguring",2);O([M()],R.prototype,"connectionError",2);O([M()],R.prototype,"setupStep",2);O([M()],R.prototype,"haUrl",2);O([M()],R.prototype,"haToken",2);O([M()],R.prototype,"pairingCode",2);O([M()],R.prototype,"pairingId",2);O([M()],R.prototype,"authUrl",2);O([M()],R.prototype,"qrDataUrl",2);O([M()],R.prototype,"isPairing",2);O([M()],R.prototype,"voiceText",2);O([M()],R.prototype,"voiceReply",2);O([M()],R.prototype,"waveData",2);O([M()],R.prototype,"pipelineStage",2);O([M()],R.prototype,"theme",2);O([M()],R.prototype,"alwaysOnEnabled",2);O([M()],R.prototype,"rooms",2);O([M()],R.prototype,"scenes",2);O([M()],R.prototype,"probeStatus",2);R=O([N("smart-app-shell")],R);

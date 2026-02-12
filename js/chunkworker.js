self.onmessage = async ({ data: url }) => {
    const res = await fetch(url);
    const blob = await res.blob();
    const ds = new DecompressionStream('gzip');
    const text = await new Response(blob.stream().pipeThrough(ds)).blob().then(b => b.text());
    self.postMessage(JSON.parse(text));
};
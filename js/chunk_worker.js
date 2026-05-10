self.onmessage = async ({ data: url }) => {
    try {
        const res = await fetch(url);
        if(!res.ok) throw new Error(`Failed to fetch ${url}`);

        const blob = await res.blob();
        
        const ds = new DecompressionStream('gzip');

        const text = await new Response(blob.stream().pipeThrough(ds)).blob().then(b => b.text());

        self.postMessage(JSON.parse(text));

    } catch (err) {
        self.reportError(err)
    }
};
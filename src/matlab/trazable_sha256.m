function value=trazable_sha256(input,kind)
% SHA-256 usando .NET de Windows: no requiere Java ni paquetes externos.
if nargin<2,kind="file";end
if kind=="file"
    fid=fopen(input,'rb');assert(fid>=0,'Trazable:File','Archivo no accesible: %s',input);
    closeFile=onCleanup(@()fclose(fid));bytes=fread(fid,Inf,'*uint8');
else
    bytes=unicode2native(char(input),'UTF-8');
end
algorithm=System.Security.Cryptography.SHA256.Create();
dispose=onCleanup(@()algorithm.Dispose());
digest=uint8(algorithm.ComputeHash(bytes));
value=string(lower(reshape(dec2hex(digest,2).',1,[])));
end
